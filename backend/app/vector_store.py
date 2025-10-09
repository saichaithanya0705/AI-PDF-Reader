"""
Vector Store Service using FAISS for fast similarity search
"""
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import faiss
from dataclasses import dataclass
import pickle
from pathlib import Path


@dataclass
class SearchResult:
    """Result from vector similarity search"""
    chunk_id: str
    document_id: str
    chunk_text: str
    page_number: int
    chunk_index: int
    similarity_score: float
    metadata: Dict[str, Any]


class VectorStore:
    """FAISS-based vector store for similarity search"""
    
    def __init__(self, embedding_dim: int = 384):
        """
        Initialize the vector store
        
        Args:
            embedding_dim: Dimension of embedding vectors
        """
        self.embedding_dim = embedding_dim
        
        # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(embedding_dim)
        
        # Store metadata for each vector
        self.chunk_metadata: List[Dict[str, Any]] = []
        
        # Track document chunks
        self.document_chunks: Dict[str, List[int]] = {}  # document_id -> list of indices
        
        print(f"✅ Initialized FAISS vector store with dimension {embedding_dim}")
    
    def add_embeddings(
        self,
        embeddings: List[List[float]],
        chunk_data: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Add embeddings to the vector store
        
        Args:
            embeddings: List of embedding vectors
            chunk_data: List of metadata for each chunk
            
        Returns:
            List of indices where vectors were added
        """
        if not embeddings or not chunk_data:
            return []
        
        if len(embeddings) != len(chunk_data):
            raise ValueError("Number of embeddings must match number of chunk data")
        
        # Convert to numpy array
        vectors = np.array(embeddings, dtype='float32')
        
        # Normalize vectors for cosine similarity
        faiss.normalize_L2(vectors)
        
        # Get starting index
        start_idx = self.index.ntotal
        
        # Add to FAISS index
        self.index.add(vectors)
        
        # Store metadata
        indices = []
        for i, data in enumerate(chunk_data):
            idx = start_idx + i
            self.chunk_metadata.append(data)
            indices.append(idx)
            
            # Track document chunks
            doc_id = data.get('document_id', '')
            if doc_id:
                if doc_id not in self.document_chunks:
                    self.document_chunks[doc_id] = []
                self.document_chunks[doc_id].append(idx)
        
        print(f"✅ Added {len(embeddings)} vectors to store (total: {self.index.ntotal})")
        
        return indices
    
    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for similar vectors
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            document_id: Optional document ID to filter results
            
        Returns:
            List of SearchResult objects
        """
        if self.index.ntotal == 0:
            print("⚠️ Vector store is empty, no results to return")
            return []
        
        try:
            # Convert to numpy array and normalize
            query_vector = np.array([query_embedding], dtype='float32')
            faiss.normalize_L2(query_vector)
            
            # Search
            # If filtering by document, search more and then filter
            search_k = top_k * 3 if document_id else top_k
            search_k = min(search_k, self.index.ntotal)
            
            distances, indices = self.index.search(query_vector, search_k)
            
            # Build results
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self.chunk_metadata):
                    continue
                
                metadata = self.chunk_metadata[idx]
                
                # Filter by document if specified
                if document_id and metadata.get('document_id') != document_id:
                    continue
                
                results.append(SearchResult(
                    chunk_id=metadata.get('chunk_id', f'chunk_{idx}'),
                    document_id=metadata.get('document_id', ''),
                    chunk_text=metadata.get('chunk_text', ''),
                    page_number=metadata.get('page_number', 0),
                    chunk_index=metadata.get('chunk_index', 0),
                    similarity_score=float(dist),
                    metadata=metadata.get('metadata', {})
                ))
                
                # Stop if we have enough results
                if len(results) >= top_k:
                    break
            
            return results
            
        except Exception as e:
            print(f"❌ Error searching vector store: {str(e)}")
            return []
    
    def remove_document(self, document_id: str) -> int:
        """
        Remove all chunks for a document
        Note: FAISS doesn't support efficient deletion, so this marks chunks as deleted
        
        Args:
            document_id: Document ID to remove
            
        Returns:
            Number of chunks marked as deleted
        """
        if document_id not in self.document_chunks:
            return 0
        
        indices = self.document_chunks[document_id]
        
        # Mark metadata as deleted (simple approach)
        for idx in indices:
            if idx < len(self.chunk_metadata):
                self.chunk_metadata[idx]['deleted'] = True
        
        # Remove from tracking
        del self.document_chunks[document_id]
        
        print(f"✅ Marked {len(indices)} chunks as deleted for document {document_id}")
        
        return len(indices)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        return {
            'total_vectors': self.index.ntotal,
            'embedding_dim': self.embedding_dim,
            'num_documents': len(self.document_chunks),
            'chunks_per_document': {
                doc_id: len(indices) 
                for doc_id, indices in self.document_chunks.items()
            }
        }
    
    def save(self, path: str):
        """
        Save the vector store to disk
        
        Args:
            path: Path to save the store
        """
        try:
            save_path = Path(path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, str(save_path) + '.faiss')
            
            # Save metadata
            with open(str(save_path) + '.meta', 'wb') as f:
                pickle.dump({
                    'chunk_metadata': self.chunk_metadata,
                    'document_chunks': self.document_chunks,
                    'embedding_dim': self.embedding_dim
                }, f)
            
            print(f"✅ Saved vector store to {path}")
            
        except Exception as e:
            print(f"❌ Error saving vector store: {str(e)}")
            raise
    
    def load(self, path: str):
        """
        Load the vector store from disk
        
        Args:
            path: Path to load the store from
        """
        try:
            load_path = Path(path)
            
            # Load FAISS index
            self.index = faiss.read_index(str(load_path) + '.faiss')
            
            # Load metadata
            with open(str(load_path) + '.meta', 'rb') as f:
                data = pickle.load(f)
                self.chunk_metadata = data['chunk_metadata']
                self.document_chunks = data['document_chunks']
                self.embedding_dim = data['embedding_dim']
            
            print(f"✅ Loaded vector store from {path}")
            print(f"   Total vectors: {self.index.ntotal}")
            print(f"   Documents: {len(self.document_chunks)}")
            
        except Exception as e:
            print(f"❌ Error loading vector store: {str(e)}")
            raise


# Global instance
_vector_store_instance = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore(embedding_dim=384)
    return _vector_store_instance
