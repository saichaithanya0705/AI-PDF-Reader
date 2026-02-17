"""
RAG (Retrieval-Augmented Generation) Service
Coordinates chunking, embedding, vector search, and LLM generation
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import time

from .chunking_service import chunking_service, DocumentChunk
from .embedding_service import get_embedding_service
from .vector_store import get_vector_store, SearchResult
from sentence_transformers import CrossEncoder
import os

# Import appropriate database based on configuration
USE_SUPABASE = os.getenv("USE_SUPABASE", "false").lower() == "true"
if USE_SUPABASE:
    from .supabase_database import get_supabase_db
    db = get_supabase_db()
else:
    from .database import db


class RAGService:
    """Service for RAG operations"""
    
    def __init__(self):
        """Initialize RAG service"""
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.chunking_service = chunking_service
        
        # Initialize Cross-Encoder for re-ranking
        try:
            self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            print("✅ Cross-Encoder initialized")
        except Exception as e:
            print(f"⚠️ Cross-Encoder initialization failed: {e}")
            self.cross_encoder = None
            
        print("✅ RAG Service initialized")
    
    async def process_document(
        self,
        document_id: str,
        pdf_path: str,
        user_id: Optional[str] = None,
        batch_size: int = 32
    ) -> Dict[str, Any]:
        """
        Process a document for RAG: chunk, embed, and store
        
        Args:
            document_id: Document ID
            pdf_path: Path to PDF file
            user_id: User ID (required for Supabase)
            batch_size: Batch size for embedding generation
            
        Returns:
            Dict with processing statistics
        """
        start_time = time.time()
        
        try:
            print(f"🔄 Processing document {document_id} for RAG...")
            
            # Step 1: Chunk the document
            print("  1️⃣ Chunking document...")
            chunks = self.chunking_service.chunk_document(pdf_path, document_id)
            
            if not chunks:
                return {
                    'success': False,
                    'error': 'No chunks created from document',
                    'chunks_created': 0
                }
            
            print(f"  ✅ Created {len(chunks)} chunks")
            
            # Step 1.5: Extract Metadata (New)
            if USE_SUPABASE and user_id:
                try:
                    print("  1️⃣.5️⃣ Extracting document metadata...")
                    from .metadata_extractor import get_metadata_extractor
                    metadata_extractor = get_metadata_extractor()
                    
                    # Reconstruct first part of text for analysis
                    # Use first 3 chunks or up to 15k chars
                    full_text = "\n".join([chunk.text for chunk in chunks[:5]])
                    
                    metadata = await metadata_extractor.extract_metadata(full_text)
                    print(f"  ✅ Extracted metadata: {metadata.get('document_type', 'Unknown')}")
                    
                    # Update document in DB
                    db.update_document(document_id, user_id, metadata=metadata)
                    print("  ✅ Updated document metadata in DB")
                    
                except Exception as e:
                    print(f"  ⚠️ Warning: Failed to extract metadata: {e}")
            
            # Step 2: Generate embeddings
            print("  2️⃣ Generating embeddings...")
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_service.generate_embeddings_batch(
                chunk_texts,
                batch_size=batch_size,
                show_progress=True
            )
            print(f"  ✅ Generated {len(embeddings)} embeddings")
            
            # Step 3: Store in database
            print("  3️⃣ Storing chunks in database...")
            chunk_ids = []
            for chunk, embedding in zip(chunks, embeddings):
                if USE_SUPABASE and user_id:
                    chunk_id = db.store_chunk(
                        user_id=user_id,
                        document_id=chunk.document_id,
                        chunk_text=chunk.text,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        embedding=embedding,
                        char_count=chunk.metadata.get('char_count'),
                        word_count=chunk.metadata.get('word_count')
                    )
                else:
                    chunk_id = db.store_chunk(
                        document_id=chunk.document_id,
                        chunk_text=chunk.text,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        embedding=embedding,
                        char_count=chunk.metadata.get('char_count'),
                        word_count=chunk.metadata.get('word_count')
                    )
                chunk_ids.append(chunk_id)
            print(f"  ✅ Stored {len(chunk_ids)} chunks in database")
            
            # Step 4: Add to vector store
            # Only add to local vector store if NOT using Supabase (Supabase stores embeddings in DB)
            if not USE_SUPABASE:
                print("  4️⃣ Adding to vector store...")
                chunk_metadata = [
                    {
                        'chunk_id': chunk_id,
                        'document_id': chunk.document_id,
                        'user_id': user_id,
                        'chunk_text': chunk.text,
                        'page_number': chunk.page_number,
                        'chunk_index': chunk.chunk_index,
                        'metadata': chunk.metadata
                    }
                    for chunk_id, chunk in zip(chunk_ids, chunks)
                ]
                
                indices = self.vector_store.add_embeddings(embeddings, chunk_metadata)
                print(f"  ✅ Added {len(indices)} vectors to store")
            else:
                print("  4️⃣ Skipped adding to local vector store (using Supabase pgvector)")
                indices = []
            
            elapsed = time.time() - start_time
            
            return {
                'success': True,
                'document_id': document_id,
                'chunks_created': len(chunks),
                'embeddings_generated': len(embeddings),
                'chunks_stored': len(chunk_ids),
                'vectors_added': len(indices),
                'elapsed_seconds': round(elapsed, 2)
            }
            
        except Exception as e:
            print(f"❌ Error processing document {document_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'document_id': document_id
            }
    
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
        Re-rank search results using Cross-Encoder
        """
        if not self.cross_encoder or not results:
            return results[:top_k]
            
        print(f"🔄 Re-ranking {len(results)} results...")
        try:
            # Prepare pairs for cross-encoder
            pairs = [[query, result.chunk_text] for result in results]
            
            # Predict scores
            scores = self.cross_encoder.predict(pairs)
            
            # Attach scores to results
            for result, score in zip(results, scores):
                # Cross-encoder scores are logits or raw scores, not necessarily 0-1
                # We update the similarity score (or could add a separate rerank_score field)
                result.similarity_score = float(score)
            
            # Sort by new score (descending)
            reranked_results = sorted(results, key=lambda x: x.similarity_score, reverse=True)
            
            return reranked_results[:top_k]
            
        except Exception as e:
            print(f"⚠️ Re-ranking failed: {e}")
            return results[:top_k]

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
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
            user_id: Optional user ID to filter results
            llm_provider: Optional LLM provider for query expansion
            use_advanced_rag: Whether to use expansion and re-ranking
            
        Returns:
            List of SearchResult objects
        """
        try:
            search_query = query
            
            # 1. Query Expansion (if enabled and provider available)
            if use_advanced_rag and llm_provider:
                 print("🚀 Using Advanced RAG: Query Expansion")
                 search_query = await self.expand_query(query, llm_provider)
            
            # Generate embedding for query
            query_embedding = self.embedding_service.generate_embedding(search_query)
            
            # Fetch more candidates for re-ranking
            # If re-ranking is enabled, fetch 3x candidates
            fetch_k = top_k * 3 if (use_advanced_rag and self.cross_encoder) else top_k
            
            if USE_SUPABASE:
                # Search using Supabase pgvector
                results_data = db.search_vectors(
                    query_embedding=query_embedding,
                    match_threshold=0.1, # Lower threshold to get more candidates (0.3 was too high)
                    match_count=fetch_k,
                    user_id=user_id,
                    document_id=document_id
                )
                
                # Map to SearchResult objects
                results = []
                for item in results_data:
                    results.append(SearchResult(
                        chunk_id=item.get('id'),
                        document_id=item.get('document_id'),
                        chunk_text=item.get('chunk_text'),
                        chunk_index=item.get('chunk_index'),
                        page_number=item.get('page_number'),
                        similarity_score=item.get('similarity'),
                        metadata=item.get('metadata'),
                        user_id=user_id
                    ))
            else:
                # Search vector store (FAISS)
                results = self.vector_store.search_similar(
                    query_embedding,
                    top_k=fetch_k,
                    document_id=document_id,
                    user_id=user_id
                )
                
            # 2. Re-ranking (if enabled)
            if use_advanced_rag and self.cross_encoder and results:
                print("🚀 Using Advanced RAG: Re-ranking")
                results = self.rerank_results(query, results, top_k)
            
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
                # No relevant chunks found
                # Still try to answer if it's general chat, but warn about no context
                prompt = f"""You are a helpful AI assistant.
                
User question: {query}

Answer: I don't have any relevant specific information in the uploaded documents to answer this question detailedly. I will try to answer based on general knowledge if possible."""
                
                # If we have history, use it
                messages = []
                if conversation_history:
                    messages.extend(conversation_history)
                messages.append({"role": "user", "content": prompt})
                
                # Use generate_chat_response if available (for history support)
                # But llm_provider here might be the raw provider or the service wrapper?
                # Assuming input llm_provider has generate_chat_response
                if hasattr(llm_provider, 'generate_chat_response'):
                    response_text = await llm_provider.generate_chat_response(messages)
                else:
                    response_text = await llm_provider.generate_text(str(messages), max_tokens=max_tokens)
                
                return {
                    'response': response_text,
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
                    'similarity': round(result.similarity_score, 3),
                    'document_id': result.document_id,
                    'document_name': (result.metadata or {}).get('document_name', 'Unknown')
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
                'response': f"Sorry, I encountered an error while searching your documents: {str(e)}",
                'sources': [],
                'has_context': False,
                'error': str(e)
            }
    
    def delete_document_from_rag(self, document_id: str) -> Dict[str, Any]:
        """
        Remove a document from RAG system
        
        Args:
            document_id: Document ID to remove
            
        Returns:
            Dict with deletion statistics
        """
        try:
            # Remove from database
            chunks_deleted = db.delete_chunks_by_document(document_id)
            
            # Remove from vector store
            if not USE_SUPABASE:
                vectors_removed = self.vector_store.remove_document(document_id)
            else:
                vectors_removed = 0
            
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        vector_stats = self.vector_store.get_stats()
        total_chunks = db.get_chunk_count()
        
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
