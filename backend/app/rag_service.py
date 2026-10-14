"""
RAG (Retrieval-Augmented Generation) Service
Coordinates chunking, embedding, vector search, and LLM generation
"""
from collections import Counter
from datetime import datetime
import math
import re
from typing import List, Dict, Any, Optional, Tuple

from .persistence import db
from .embedding_service import get_embedding_service
from .ingestion_service import get_ingestion_service
from .reranker_service import RerankerServiceUnavailableError, get_reranker_service
from .semantic_cache import SemanticCacheContext, get_semantic_search_cache
from .vector_store import get_vector_store, SearchResult
import os

# Side-panel matches below this retrieval score are unrelated filler. Measured
# with NVIDIA nemotron embeddings: correct cross-PDF matches scored >= 0.24 and
# clearly unrelated ones 0.11-0.20; the floor sits at the midpoint. Re-check
# with the evals (cross_doc_off_topic, cross_doc_hit@3) if the model changes.
CROSS_DOCUMENT_MIN_SCORE = float(os.getenv("RECOMMENDATION_MIN_SCORE", "0.22"))


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bounded_similarity(value: Any) -> float:
    score = _optional_float(value)
    if score is None:
        return 0.0
    return max(0.0, min(1.0, score))


def retrieval_score_fields(result: SearchResult) -> Dict[str, Any]:
    """Return explicit retrieval score fields for API responses."""
    metadata = getattr(result, "metadata", None) or {}
    vector_similarity = _bounded_similarity(
        metadata.get("vector_similarity", getattr(result, "similarity_score", 0.0))
    )

    retrieval_score = _optional_float(metadata.get("retrieval_score"))
    lexical_overlap = _optional_float(metadata.get("lexical_overlap"))
    keyword_score = _optional_float(metadata.get("keyword_score"))
    bm25_score = _optional_float(metadata.get("bm25_score"))
    rerank_score = _optional_float(metadata.get("rerank_score"))
    recency_score = _optional_float(metadata.get("recency_score"))

    return {
        "similarity": round(vector_similarity, 3),
        "vector_similarity": round(vector_similarity, 3),
        "retrieval_score": round(retrieval_score, 4) if retrieval_score is not None else None,
        "lexical_overlap": round(lexical_overlap, 4) if lexical_overlap is not None else None,
        "keyword_score": round(keyword_score, 4) if keyword_score is not None else None,
        "bm25_score": round(bm25_score, 4) if bm25_score is not None else None,
        "rerank_score": round(rerank_score, 4) if rerank_score is not None else None,
        "recency_score": round(recency_score, 4) if recency_score is not None else None,
        "recency_intent": metadata.get("recency_intent"),
        "recency_source": metadata.get("recency_source"),
        "recency_timestamp": metadata.get("recency_timestamp"),
        "retrieval_cache_hit": metadata.get("retrieval_cache_hit", False),
        "retrieval_cache_hit_type": metadata.get("retrieval_cache_hit_type"),
        "retrieval_cache_similarity": metadata.get("retrieval_cache_similarity"),
    }


def format_retrieval_result(result: SearchResult, snippet_chars: int = 200) -> Dict[str, Any]:
    """Format a vector search result without hiding score semantics."""
    metadata = getattr(result, "metadata", None) or {}
    chunk_text = getattr(result, "chunk_text", "") or ""
    snippet = chunk_text[:snippet_chars] + ("..." if len(chunk_text) > snippet_chars else "")

    formatted = {
        "id": getattr(result, "chunk_id", None) or "unknown",
        "document_id": getattr(result, "document_id", None),
        "document_name": (
            metadata.get("document_name")
            or metadata.get("original_name")
            or metadata.get("filename")
            or "Unknown Document"
        ),
        "page_number": getattr(result, "page_number", None) or 1,
        "section_title": metadata.get("section_title") or metadata.get("heading") or "Relevant section",
        "text": snippet,
        "file_path": metadata.get("file_path", ""),
    }
    formatted.update(retrieval_score_fields(result))
    return formatted


class RAGService:
    """Service for RAG operations"""
    
    def __init__(self):
        """Initialize RAG service"""
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.ingestion_service = get_ingestion_service()
        self.semantic_cache = get_semantic_search_cache()
        
        self.reranker = get_reranker_service()
            
        print("✅ RAG Service initialized")
    
    async def process_document(
        self,
        document_id: str,
        pdf_path: str,
        user_id: Optional[str] = None,
        mode: str = "single",
        batch_size: int = 32
    ) -> Dict[str, Any]:
        """
        Process a document for RAG: chunk, embed, and store
        
        Args:
            document_id: Document ID
            pdf_path: Path to PDF file
            user_id: Authenticated user ID for tenant filtering
            batch_size: Batch size for embedding generation
            
        Returns:
            Dict with processing statistics
        """
        if not user_id:
            return {
                'success': False,
                'error': 'user_id is required for document ingestion',
                'document_id': document_id,
            }

        return await self.ingestion_service.process_document(
            document_id=document_id,
            user_id=user_id,
            mode=mode,
            batch_size=batch_size,
        )
    
    async def expand_query(self, query: str, llm_provider) -> str:
        """
        Expand/Optimize user query for better retrieval
        """
        try:
            # Simple query expansion prompt
            prompt = f"""You are an AI assistant that optimizes search queries for retrieving information from documents.
            
            User Query: "{query}"
            
            Instructions:
            1. Rewrite the query to be more specific and keyword-rich to improve vector search retrieval.
            2. If the query is vague, add relevant context or synonyms.
            3. Do NOT change the core meaning or intent.
            4. Output ONLY the improved query text, nothing else.
            
            Optimized Query:"""
            
            response = await llm_provider.generate_text(prompt, max_tokens=100)
            optimized_query = response.content.strip()
            # Remove any potential quotes or prefixes
            if optimized_query.startswith('"') and optimized_query.endswith('"'):
                optimized_query = optimized_query[1:-1]
            elif optimized_query.startswith("Optimized Query:"):
                 optimized_query = optimized_query.replace("Optimized Query:", "").strip()

            print(f"Original Query: {query}")
            print(f"Optimized Query: {optimized_query}")
            return optimized_query
        except Exception as e:
            print(f"⚠️ Query expansion failed: {e}")
            return query

    def rerank_results(self, query: str, results: List[SearchResult], top_k: int) -> List[SearchResult]:
        """
        Re-rank search results using NVIDIA's hosted reranking model.
        """
        if not results:
            return results[:top_k]
        try:
            scores = self.reranker.rerank(query, [result.chunk_text for result in results])
            reranked_results = []
            for score in scores:
                result = results[score.index]
                if getattr(result, "metadata", None) is None:
                    result.metadata = {}
                result.metadata["vector_similarity"] = result.similarity_score
                result.metadata["rerank_score"] = score.logit
                reranked_results.append(result)
            return reranked_results[:top_k]
        except RerankerServiceUnavailableError:
            return results[:top_k]

    def _candidate_count(self, top_k: int, use_advanced_rag: bool) -> int:
        requested = max(1, min(int(top_k or 1), 50))
        if not use_advanced_rag:
            return requested
        return min(max(requested * 8, requested + 10), 80)

    def _tokenize_terms(self, text: str) -> List[str]:
        stopwords = {
            "the", "and", "for", "with", "that", "this", "from", "into", "are",
            "was", "were", "you", "your", "about", "what", "when", "where",
            "which", "who", "how", "why", "pdf", "document",
        }
        return [
            term
            for term in re.findall(r"[A-Za-z0-9]{3,}", (text or "").lower())
            if term not in stopwords
        ]

    def _keyword_haystack(self, result: SearchResult) -> str:
        metadata = getattr(result, "metadata", None) or {}
        return " ".join(
            str(part or "")
            for part in [
                getattr(result, "chunk_text", ""),
                metadata.get("section_title"),
                metadata.get("document_name"),
                metadata.get("original_name"),
                metadata.get("filename"),
            ]
        )

    def _keyword_scores(self, query: str, results: List[SearchResult]) -> List[Dict[str, float]]:
        query_terms = self._tokenize_terms(query)
        if not query_terms or not results:
            return [
                {"lexical_overlap": 0.0, "bm25_score": 0.0, "keyword_score": 0.0}
                for _ in results
            ]

        query_unique_terms = set(query_terms)
        documents = [self._tokenize_terms(self._keyword_haystack(result)) for result in results]
        document_count = len(documents)
        avg_doc_length = sum(len(doc) for doc in documents) / max(document_count, 1)
        document_frequency = Counter(
            term
            for term in query_unique_terms
            for doc in documents
            if term in set(doc)
        )

        raw_bm25_scores: List[float] = []
        lexical_scores: List[float] = []
        k1 = 1.5
        b = 0.75

        for doc_terms in documents:
            term_counts = Counter(doc_terms)
            doc_length = len(doc_terms) or 1
            lexical_scores.append(
                sum(1 for term in query_unique_terms if term in term_counts) / len(query_unique_terms)
            )

            score = 0.0
            for term in query_terms:
                term_frequency = term_counts.get(term, 0)
                if term_frequency == 0:
                    continue
                df = document_frequency.get(term, 0)
                idf = math.log(1 + ((document_count - df + 0.5) / (df + 0.5)))
                denominator = term_frequency + k1 * (1 - b + b * (doc_length / max(avg_doc_length, 1)))
                score += idf * ((term_frequency * (k1 + 1)) / denominator)
            raw_bm25_scores.append(score)

        max_bm25 = max(raw_bm25_scores) if raw_bm25_scores else 0.0
        normalized_bm25 = [
            (score / max_bm25) if max_bm25 > 0 else 0.0
            for score in raw_bm25_scores
        ]

        return [
            {
                "lexical_overlap": round(lexical, 4),
                "bm25_score": round(raw_bm25, 4),
                "keyword_score": round(keyword, 4),
            }
            for lexical, raw_bm25, keyword in zip(lexical_scores, raw_bm25_scores, normalized_bm25)
        ]

    def _detect_recency_intent(self, query: str) -> Optional[str]:
        normalized = (query or "").lower()
        if re.search(r"\b(recently|last)\s+opened\b|\bopened\s+recently\b", normalized):
            return "recently_opened"
        if re.search(r"\b(oldest|earliest|first uploaded|least recent)\b", normalized):
            return "oldest"
        if re.search(r"\b(latest|newest|most recent|recent|recently uploaded|last uploaded)\b", normalized):
            return "latest"
        return None

    def _timestamp_candidates(self, result: SearchResult, recency_intent: str) -> List[Tuple[str, Any]]:
        metadata = getattr(result, "metadata", None) or {}
        if recency_intent == "recently_opened":
            return [
                ("last_opened", metadata.get("last_opened")),
                ("last_accessed", metadata.get("last_accessed")),
                ("last_uploaded", metadata.get("last_uploaded")),
                ("upload_date", metadata.get("upload_date")),
            ]
        return [
            ("last_uploaded", metadata.get("last_uploaded")),
            ("upload_date", metadata.get("upload_date")),
            ("last_accessed", metadata.get("last_accessed")),
        ]

    def _parse_timestamp(self, value: Any) -> Optional[float]:
        if not value:
            return None
        if hasattr(value, "timestamp"):
            return float(value.timestamp())
        text = str(value).strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    def _recency_metadata(self, results: List[SearchResult], recency_intent: Optional[str]) -> None:
        if not recency_intent:
            return

        timestamps: List[Optional[float]] = []
        sources: List[Optional[str]] = []
        raw_values: List[Any] = []
        for result in results:
            selected_source = None
            selected_value = None
            selected_timestamp = None
            for source, value in self._timestamp_candidates(result, recency_intent):
                parsed = self._parse_timestamp(value)
                if parsed is not None:
                    selected_source = source
                    selected_value = value
                    selected_timestamp = parsed
                    break
            sources.append(selected_source)
            raw_values.append(selected_value)
            timestamps.append(selected_timestamp)

        valid_timestamps = [timestamp for timestamp in timestamps if timestamp is not None]
        if not valid_timestamps:
            return

        oldest = min(valid_timestamps)
        newest = max(valid_timestamps)
        span = max(newest - oldest, 1.0)

        for result, timestamp, source, raw_value in zip(results, timestamps, sources, raw_values):
            if getattr(result, "metadata", None) is None:
                result.metadata = {}
            if timestamp is None:
                score = 0.0
            elif recency_intent == "oldest":
                score = (newest - timestamp) / span
            else:
                score = (timestamp - oldest) / span

            result.metadata["recency_intent"] = recency_intent
            result.metadata["recency_score"] = round(float(score), 4)
            result.metadata["recency_source"] = source
            result.metadata["recency_timestamp"] = raw_value

    def _rank_vector_results(self, query: str, results: List[SearchResult], top_k: int) -> List[SearchResult]:
        keyword_scores = self._keyword_scores(query, results)
        recency_intent = self._detect_recency_intent(query)
        self._recency_metadata(results, recency_intent)

        ranked = []
        for result, keyword_metadata in zip(results, keyword_scores):
            metadata = getattr(result, "metadata", None) or {}
            vector_similarity = _bounded_similarity(getattr(result, "similarity_score", 0.0))
            keyword_score = max(
                _bounded_similarity(metadata.get("keyword_score")),
                _bounded_similarity(keyword_metadata["keyword_score"]),
            )
            existing_bm25_score = _optional_float(metadata.get("bm25_score"))
            bm25_score = max(
                existing_bm25_score if existing_bm25_score is not None else 0.0,
                float(keyword_metadata["bm25_score"]),
            )
            recency_score = _bounded_similarity(metadata.get("recency_score"))
            if recency_intent:
                retrieval_score = (0.65 * vector_similarity) + (0.15 * keyword_score) + (0.20 * recency_score)
            else:
                retrieval_score = (0.80 * vector_similarity) + (0.20 * keyword_score)
            if getattr(result, "metadata", None) is None:
                result.metadata = {}
            result.metadata["vector_similarity"] = vector_similarity
            result.metadata["lexical_overlap"] = keyword_metadata["lexical_overlap"]
            result.metadata["bm25_score"] = round(bm25_score, 4)
            result.metadata["keyword_score"] = round(keyword_score, 4)
            result.metadata["retrieval_score"] = round(retrieval_score, 4)
            result.metadata.setdefault("retrieval_source", "vector")
            ranked.append(result)

        return sorted(
            ranked,
            key=lambda x: (getattr(x, "metadata", None) or {}).get(
                "retrieval_score",
                _bounded_similarity(getattr(x, "similarity_score", 0.0)),
            ),
            reverse=True,
        )[:top_k]

    def _semantic_cache(self):
        cache = getattr(self, "semantic_cache", None)
        if cache is None:
            cache = get_semantic_search_cache()
            self.semantic_cache = cache
        return cache

    def _library_revision(self, user_id: Optional[str]) -> str:
        return self._semantic_cache().revision_for_user(user_id)

    def _search_bm25_candidates(
        self,
        query: str,
        fetch_k: int,
        document_id: Optional[str],
        exclude_document_id: Optional[str],
        user_id: Optional[str],
    ) -> List[SearchResult]:
        # Evals inject an isolated chunk store; production uses the app database.
        chunk_db = getattr(self, "chunk_search_db", None) or db
        try:
            rows = chunk_db.search_chunks_bm25(
                query=query,
                limit=fetch_k,
                document_id=document_id,
                exclude_document_id=exclude_document_id,
                client_id=user_id,
            )
        except AttributeError:
            return []
        except Exception as exc:
            print(f"⚠️ BM25 retrieval failed: {exc}")
            return []

        results: List[SearchResult] = []
        for row in rows:
            metadata = dict(row.get("metadata") or {})
            metadata.setdefault("retrieval_source", "bm25")
            results.append(
                SearchResult(
                    chunk_id=row.get("chunk_id") or row.get("id") or "",
                    document_id=row.get("document_id") or "",
                    chunk_text=row.get("chunk_text") or "",
                    chunk_index=int(row.get("chunk_index") or 0),
                    page_number=int(row.get("page_number") or 1),
                    similarity_score=0.0,
                    user_id=row.get("client_id") or user_id,
                    metadata=metadata,
                )
            )
        return results

    def _merge_retrieval_candidates(
        self,
        vector_results: List[SearchResult],
        bm25_results: List[SearchResult],
    ) -> List[SearchResult]:
        merged: Dict[str, SearchResult] = {}
        order: List[str] = []

        for result in vector_results:
            key = (
                getattr(result, "chunk_id", None)
                or f"{getattr(result, 'document_id', '')}:{getattr(result, 'page_number', '')}:{len(order)}"
            )
            if getattr(result, "metadata", None) is None:
                result.metadata = {}
            result.metadata.setdefault("retrieval_source", "vector")
            merged[key] = result
            order.append(key)

        for result in bm25_results:
            key = (
                getattr(result, "chunk_id", None)
                or f"{getattr(result, 'document_id', '')}:{getattr(result, 'page_number', '')}:{len(order)}"
            )
            if key in merged:
                existing = merged[key]
                existing_metadata = getattr(existing, "metadata", None) or {}
                bm25_metadata = getattr(result, "metadata", None) or {}
                existing_metadata.update({
                    bm25_key: bm25_value
                    for bm25_key, bm25_value in bm25_metadata.items()
                    if bm25_value is not None
                })
                existing_metadata["retrieval_source"] = "hybrid"
                existing.metadata = existing_metadata
                continue

            if getattr(result, "metadata", None) is None:
                result.metadata = {}
            result.metadata.setdefault("retrieval_source", "bm25")
            merged[key] = result
            order.append(key)

        return [merged[key] for key in order]

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        exclude_document_id: Optional[str] = None,
        user_id: Optional[str] = None,
        llm_provider = None,
        use_advanced_rag: bool = True
    ) -> List[SearchResult]:
        """
        Search for relevant document chunks
        
        Args:
            query: Search query
            top_k: Number of results to return
            document_id: Optional document ID to filter results
            exclude_document_id: Optional document ID to exclude from results
            user_id: Optional user ID to filter results
            llm_provider: Optional LLM provider for query expansion
            use_advanced_rag: Whether to use expansion and re-ranking
            
        Returns:
            List of SearchResult objects
        """
        try:
            query = (query or "").strip()
            top_k = max(1, min(int(top_k or 1), 50))
            if not query:
                return []

            semantic_cache = self._semantic_cache()
            recency_intent = self._detect_recency_intent(query)
            cache_context = SemanticCacheContext(
                user_id=user_id,
                document_id=document_id,
                exclude_document_id=exclude_document_id,
                top_k=top_k,
                use_advanced_rag=use_advanced_rag,
                library_revision=semantic_cache.revision_for_user(user_id),
                recency_intent=recency_intent,
            )
            cached_results = semantic_cache.get_exact(query, cache_context)
            if cached_results is not None:
                return cached_results

            # Embed the original user query first so near-duplicate cache hits can
            # skip query expansion, vector search, and optional re-ranking.
            query_embedding = self.embedding_service.generate_embedding(query)
            cached_results = semantic_cache.get_semantic(query_embedding, cache_context)
            if cached_results is not None:
                return cached_results

            search_query = query
            search_embedding = query_embedding
            
            # 1. Query Expansion (if enabled and provider available)
            if use_advanced_rag and llm_provider:
                 print("🚀 Using Advanced RAG: Query Expansion")
                 search_query = await self.expand_query(query, llm_provider)
                 if search_query.strip() != query:
                     search_embedding = self.embedding_service.generate_embedding(search_query)
            
            fetch_k = self._candidate_count(top_k, use_advanced_rag)
            
            vector_results = self.vector_store.search_similar(
                search_embedding,
                top_k=fetch_k,
                document_id=document_id,
                exclude_document_id=exclude_document_id,
                user_id=user_id
            )
            bm25_results = self._search_bm25_candidates(
                query=search_query,
                fetch_k=fetch_k,
                document_id=document_id,
                exclude_document_id=exclude_document_id,
                user_id=user_id,
            )
            results = self._merge_retrieval_candidates(vector_results, bm25_results)
                
            ranked_results = self._rank_vector_results(query, results, fetch_k)

            # 2. Re-ranking (if enabled). retrieval_score remains the hybrid
            # vector/keyword/recency score; rerank_score is separate metadata.
            if use_advanced_rag and ranked_results:
                print("🚀 Using Advanced RAG: Re-ranking")
                results = self.rerank_results(query, ranked_results, top_k)
            else:
                results = ranked_results[:top_k]

            semantic_cache.put(query, query_embedding, cache_context, results)
            
            return results
            
        except Exception as e:
            print(f"❌ Error searching documents: {str(e)}")

            return []
    
    async def generate_rag_response(
        self,
        query: str,
        llm_provider,
        document_id: Optional[str] = None,
        user_id: Optional[str] = None,
        top_k: int = 5,
        max_tokens: int = 500,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using RAG with Hybrid Context (Local + Global) and History
        
        Args:
            query: User query
            llm_provider: LLM provider instance
            document_id: Optional document ID to filter results (Active Document)
            user_id: Optional user ID to filter results
            top_k: Number of chunks to retrieve
            max_tokens: Maximum tokens for response
            conversation_history: List of previous messages
            
        Returns:
            Dict with response and sources
        """
        try:
            # 1. Local Search (Active Document) - High priority
            local_results = []
            if document_id:
                local_results = await self.search_documents(
                    query=query,
                    top_k=top_k,
                    document_id=document_id,
                    user_id=user_id,
                    llm_provider=llm_provider,
                    use_advanced_rag=True
                )
            
            # 2. Global Search (Library) - ONLY for library context (no specific document)
            # When document_id is provided (PDF viewer mode), we ONLY search that document
            # When document_id is None (library mode), we search across all documents
            if document_id:
                # PDF Viewer mode: only use results from the current document
                final_results = local_results
            else:
                # Library mode: search across all documents
                global_results = await self.search_documents(
                    query=query,
                    top_k=top_k,
                    document_id=None, # Search all
                    user_id=user_id,
                    llm_provider=llm_provider,
                    use_advanced_rag=True
                )
                final_results = global_results
            
            if not final_results:
                return {
                    'response': "I don't have relevant information in your uploaded documents to answer that.",
                    'sources': [],
                    'has_context': False
                }
            
            # Build context from search results
            context_parts = []
            for i, result in enumerate(final_results, 1):
                doc_name = (result.metadata or {}).get('document_name', 'Unknown')
                context_parts.append(
                    f"[Page {result.page_number}]\n{result.chunk_text}"
                )

            context = "\n\n".join(context_parts)

            # Build RAG prompt with History - different for PDF viewer vs Library mode
            if document_id:
                # PDF Viewer mode: focused on the current document only
                system_prompt = f"""You are a helpful AI assistant that answers questions based on the currently open document.

DOCUMENT CONTEXT:
{context}

INSTRUCTIONS:
- Answer the question using ONLY the information from the document context above.
- Be specific and cite page numbers when relevant.
- If the context doesn't contain the answer, say "I don't see that information in this document."
- Do NOT make up information that isn't in the document.

FORMATTING:
- Use **bold** for names, titles, and key terms
- Use bullet points (- item) for lists
- Use headings (## Section) to organize longer responses
- Keep paragraphs short and readable
- Use line breaks between sections for clarity
"""
            else:
                # Library mode: searching across all documents
                system_prompt = f"""You are a helpful AI assistant that answers questions based on the user's document library.

CONTEXT FROM LIBRARY DOCUMENTS:
{context}

INSTRUCTIONS:
- Answer the question using the information from the library documents above.
- Mention which document the information comes from when relevant.
- Be specific and cite sources.
- If the context doesn't contain the answer, say so.

FORMATTING:
- Use **bold** for names, titles, and key terms
- Use bullet points (- item) for lists
- Use headings (## Section) to organize longer responses
- Keep paragraphs short and readable
- Use line breaks between sections for clarity
"""
            
            messages = []
            messages.append({"role": "system", "content": system_prompt})
            
            if conversation_history:
                messages.extend(conversation_history)
                
            messages.append({"role": "user", "content": query})
            
            # Generate response
            if hasattr(llm_provider, 'generate_chat_response'):
                 response_text = await llm_provider.generate_chat_response(messages)
            else:
                 # Fallback for simpler providers
                 full_prompt = f"{system_prompt}\n\nUSER QUESTION: {query}"
                 resp_obj = await llm_provider.generate_text(full_prompt, max_tokens=max_tokens)
                 response_text = resp_obj.content

            # Format sources
            sources = [
                {
                    'page': result.page_number,
                    'text': result.chunk_text[:200] + '...' if len(result.chunk_text) > 200 else result.chunk_text,
                    'document_id': result.document_id,
                    'document_name': (result.metadata or {}).get('document_name', 'Unknown'),
                    **retrieval_score_fields(result),
                }
                for result in final_results
            ]
            
            return {
                'response': response_text,
                'sources': sources,
                'has_context': True,
                'num_sources': len(sources)
            }
            
        except Exception as e:
            print(f"❌ Error generating RAG response: {str(e)}")
            return {
                'response': "Sorry, I encountered an error while searching your documents.",
                'sources': [],
                'has_context': False,
                'error': 'rag_generation_failed'
            }
    
    def delete_document_from_rag(self, document_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Remove a document from RAG system
        
        Args:
            document_id: Document ID to remove
            user_id: Authenticated user ID for tenant filtering
            
        Returns:
            Dict with deletion statistics
        """
        try:
            if not user_id:
                return {
                    'success': False,
                    'document_id': document_id,
                    'error': 'user_id is required for document deletion',
                }

            document = db.get_document_by_id(document_id, client_id=user_id)
            if not document:
                return {
                    'success': False,
                    'document_id': document_id,
                    'error': 'Document not found',
                }

            chunks_deleted = db.delete_chunks_by_document(document_id, client_id=user_id)
            vectors_removed = self.vector_store.remove_document(document_id)
            
            return {
                'success': True,
                'document_id': document_id,
                'chunks_deleted': chunks_deleted,
                'vectors_removed': vectors_removed
            }
            
        except Exception as e:
            print(f"❌ Error deleting document from RAG: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get RAG system statistics"""
        vector_stats = self.vector_store.get_stats(user_id=user_id)
        total_chunks = db.get_chunk_count(client_id=user_id)
        
        return {
            'vector_store': vector_stats,
            'database': {
                'total_chunks': total_chunks
            },
            'embedding': {
                'model': self.embedding_service.model_name,
                'dimension': self.embedding_service.embedding_dim
            }
        }


# Global instance
_rag_service_instance = None


def get_rag_service() -> RAGService:
    """Get or create the global RAG service instance"""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
