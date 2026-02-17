"""
Embedding Service for RAG
Generates vector embeddings for text using SentenceTransformer
"""
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import torch


class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding service
        
        Args:
            model_name: Name of the SentenceTransformer model to use
        """
        self.model_name = model_name
        self.embedding_dim = 384  # Dimension for all-MiniLM-L6-v2
        
        print(f"🔄 Loading embedding model: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
            # Use GPU if available
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = self.model.to(device)
            print(f"✅ Embedding model loaded successfully on {device}")
            print(f"   Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            print(f"❌ Error loading embedding model: {str(e)}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            if not text or not text.strip():
                # Return zero vector for empty text
                return [0.0] * self.embedding_dim
            
            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Normalize for cosine similarity
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding.tolist()
            
        except Exception as e:
            print(f"❌ Error generating embedding: {str(e)}")
            # Return zero vector on error
            return [0.0] * self.embedding_dim
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (more efficient)
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            show_progress: Whether to show progress bar
            
        Returns:
            List of embedding vectors
        """
        try:
            if not texts:
                return []
            
            # Filter out empty texts but keep track of indices
            non_empty_texts = []
            non_empty_indices = []
            for i, text in enumerate(texts):
                if text and text.strip():
                    non_empty_texts.append(text)
                    non_empty_indices.append(i)
            
            if not non_empty_texts:
                # All texts are empty
                return [[0.0] * self.embedding_dim] * len(texts)
            
            # Generate embeddings for non-empty texts
            embeddings = self.model.encode(
                non_empty_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=show_progress
            )
            
            # Normalize embeddings
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = np.where(norms > 0, embeddings / norms, embeddings)
            
            # Create result list with zero vectors for empty texts
            result = [[0.0] * self.embedding_dim] * len(texts)
            
            # Fill in embeddings for non-empty texts
            for i, idx in enumerate(non_empty_indices):
                result[idx] = embeddings[i].tolist()
            
            return result
            
        except Exception as e:
            print(f"❌ Error generating batch embeddings: {str(e)}")
            # Return zero vectors on error
            return [[0.0] * self.embedding_dim] * len(texts)
    
    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Dot product of normalized vectors = cosine similarity
            similarity = np.dot(vec1, vec2)
            
            # Clamp to [0, 1] range
            return float(max(0.0, min(1.0, similarity)))
            
        except Exception as e:
            print(f"❌ Error computing similarity: {str(e)}")
            return 0.0


# Global instance - will be initialized when imported
_embedding_service_instance = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance"""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance


# For convenience
def generate_embedding(text: str) -> List[float]:
    """Generate embedding for a single text"""
    return get_embedding_service().generate_embedding(text)


def generate_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Generate embeddings for multiple texts"""
    return get_embedding_service().generate_embeddings_batch(texts, batch_size)
