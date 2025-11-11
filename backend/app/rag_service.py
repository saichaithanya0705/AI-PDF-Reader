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
            print("  4️⃣ Adding to vector store...")
            chunk_metadata = [
                {
                    'chunk_id': chunk_id,
                    'document_id': chunk.document_id,
                    'chunk_text': chunk.text,
                    'page_number': chunk.page_number,
                    'chunk_index': chunk.chunk_index,
                    'metadata': chunk.metadata
                }
                for chunk_id, chunk in zip(chunk_ids, chunks)
            ]
            
            indices = self.vector_store.add_embeddings(embeddings, chunk_metadata)
            print(f"  ✅ Added {len(indices)} vectors to store")
            
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
    
    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for relevant document chunks
        
        Args:
            query: Search query
            top_k: Number of results to return
            document_id: Optional document ID to filter results
            
        Returns:
            List of SearchResult objects
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Search vector store
            results = self.vector_store.search_similar(
                query_embedding,
                top_k=top_k,
                document_id=document_id
            )
            
            return results
            
        except Exception as e:
            print(f"❌ Error searching documents: {str(e)}")
            return []
    
    async def generate_rag_response(
        self,
        query: str,
        llm_provider,
        document_id: Optional[str] = None,
        top_k: int = 5,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        Generate a response using RAG
        
        Args:
            query: User query
            llm_provider: LLM provider instance
            document_id: Optional document ID to filter results
            top_k: Number of chunks to retrieve
            max_tokens: Maximum tokens for response
            
        Returns:
            Dict with response and sources
        """
        try:
            # Search for relevant chunks
            search_results = await self.search_documents(
                query=query,
                top_k=top_k,
                document_id=document_id
            )
            
            if not search_results:
                # No relevant chunks found
                prompt = f"""You are a helpful AI assistant.
                
User question: {query}

Answer: I don't have any relevant information in the uploaded documents to answer this question. Please ask about content from the uploaded PDFs."""
                
                response = await llm_provider.generate_text(prompt, max_tokens=max_tokens)
                
                return {
                    'response': response.content,
                    'sources': [],
                    'has_context': False
                }
            
            # Build context from search results
            context_parts = []
            for i, result in enumerate(search_results, 1):
                context_parts.append(
                    f"[Source {i} - Page {result.page_number}, Score: {result.similarity_score:.2f}]\n{result.chunk_text}"
                )
            
            context = "\n\n".join(context_parts)
            
            # Build RAG prompt
            prompt = f"""You are a helpful AI assistant that answers questions based on provided document context.

CONTEXT FROM DOCUMENTS:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
- Answer the question using ONLY the information from the context above
- Be specific and cite which source(s) you're using (e.g., "According to Source 1...")
- If the context doesn't contain enough information to fully answer the question, say so
- Keep your answer concise and accurate
- Don't make up information not present in the context

ANSWER:"""
            
            # Generate response
            response = await llm_provider.generate_text(prompt, max_tokens=max_tokens)
            
            # Format sources
            sources = [
                {
                    'page': result.page_number,
                    'text': result.chunk_text[:200] + '...' if len(result.chunk_text) > 200 else result.chunk_text,
                    'similarity': round(result.similarity_score, 3),
                    'document_id': result.document_id
                }
                for result in search_results
            ]
            
            return {
                'response': response.content,
                'sources': sources,
                'has_context': True,
                'num_sources': len(sources)
            }
            
        except Exception as e:
            print(f"❌ Error generating RAG response: {str(e)}")
            return {
                'response': f"Sorry, I encountered an error: {str(e)}",
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
