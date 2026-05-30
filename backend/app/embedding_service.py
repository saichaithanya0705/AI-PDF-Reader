"""
Embedding Service for RAG
Generates vector embeddings for text using SentenceTransformer or Transformers fallback
"""
from typing import List
import numpy as np
import os
import torch


class EmbeddingServiceUnavailableError(RuntimeError):
    """Raised when embeddings are requested before a real model is available."""


class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self, model_name: str = None):
        """
        Initialize the embedding service
        
        Args:
            model_name: Name of the SentenceTransformer model to use
        """
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
        self.embedding_dim = 384  # Dimension for all-MiniLM-L6-v2
        self.model = None
        self.tokenizer = None
        self.transformers_model = None
        self.use_transformers_fallback = False
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.load_error = None
        
        print(f"[*] Loading embedding model: {self.model_name}")
        
        # Try sentence_transformers first
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self.model = self.model.to(self.device)
            self.embedding_dim = int(self.model.get_sentence_embedding_dimension())
            print(f"[OK] sentence_transformers loaded successfully on {self.device}")
            print(f"     Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            print(f"[ERROR] Error loading sentence_transformers: {str(e)}")
            print(f"[*] Attempting fallback to transformers library...")
            
            # Try transformers library as fallback
            try:
                from transformers import AutoTokenizer, AutoModel
                
                # Use the same model but via transformers
                model_path = self.model_name
                if "/" not in model_path:
                    model_path = f"sentence-transformers/{model_path}"
                print(f"     Loading tokenizer from: {model_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                
                print(f"     Loading model from: {model_path}")
                self.transformers_model = AutoModel.from_pretrained(model_path)
                self.transformers_model = self.transformers_model.to(self.device)
                self.embedding_dim = int(getattr(self.transformers_model.config, "hidden_size", self.embedding_dim))
                self.use_transformers_fallback = True
                
                print(f"[OK] Transformers fallback loaded successfully on {self.device}")
                print(f"     Embedding dimension: {self.embedding_dim}")
            except Exception as fallback_error:
                print(f"[ERROR] Error loading transformers fallback: {str(fallback_error)}")
                print("[ERROR] Embedding service unavailable; refusing to generate fake vectors.")
                self.model = None
                self.transformers_model = None
                self.load_error = fallback_error

    def _ensure_model_loaded(self) -> None:
        if self.model is None and self.transformers_model is None:
            detail = f": {self.load_error}" if self.load_error else ""
            raise EmbeddingServiceUnavailableError(
                f"Embedding model '{self.model_name}' is not available{detail}"
            )
    
    def _mean_pooling(self, model_output, attention_mask):
        """Mean pooling - take average of all tokens"""
        token_embeddings = model_output[0]  # First element contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            self._ensure_model_loaded()

            if not text or not text.strip():
                return [0.0] * self.embedding_dim
            
            # Use sentence_transformers if available
            if self.model is not None:
                embedding = self.model.encode(
                    text,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )

                return embedding.tolist()
            
            # Use transformers fallback
            elif self.use_transformers_fallback and self.transformers_model is not None:
                # Tokenize
                encoded_input = self.tokenizer(
                    text,
                    padding=True,
                    truncation=True,
                    return_tensors='pt',
                    max_length=512
                )
                
                # Move to device
                encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}
                
                # Compute token embeddings
                with torch.no_grad():
                    model_output = self.transformers_model(**encoded_input)
                
                # Perform pooling
                sentence_embedding = self._mean_pooling(model_output, encoded_input['attention_mask'])
                
                # Normalize
                sentence_embedding = torch.nn.functional.normalize(sentence_embedding, p=2, dim=1)
                
                # Convert to list
                embedding = sentence_embedding.cpu().numpy()[0]
                return embedding.tolist()
            
            else:
                raise EmbeddingServiceUnavailableError(f"Embedding model '{self.model_name}' is not available")
            
        except Exception as e:
            print(f"[ERROR] Error generating embedding: {str(e)}")
            raise e
    
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
            
            self._ensure_model_loaded()
            
            # Filter out empty texts but keep track of indices
            non_empty_texts = []
            non_empty_indices = []
            for i, text in enumerate(texts):
                if text and text.strip():
                    non_empty_texts.append(text)
                    non_empty_indices.append(i)
            
            if not non_empty_texts:
                return [[0.0] * self.embedding_dim] * len(texts)
            
            # Use sentence_transformers if available
            if self.model is not None:
                embeddings = self.model.encode(
                    non_empty_texts,
                    batch_size=batch_size,
                    convert_to_numpy=True,
                    show_progress_bar=show_progress,
                    normalize_embeddings=True,
                )
                
            # Use transformers fallback
            elif self.use_transformers_fallback and self.transformers_model is not None:
                all_embeddings = []
                
                # Process in batches
                for i in range(0, len(non_empty_texts), batch_size):
                    batch_texts = non_empty_texts[i:i + batch_size]
                    
                    # Tokenize batch
                    encoded_input = self.tokenizer(
                        batch_texts,
                        padding=True,
                        truncation=True,
                        return_tensors='pt',
                        max_length=512
                    )
                    
                    # Move to device
                    encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}
                    
                    # Compute embeddings
                    with torch.no_grad():
                        model_output = self.transformers_model(**encoded_input)
                    
                    # Perform pooling
                    batch_embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])
                    
                    # Normalize
                    batch_embeddings = torch.nn.functional.normalize(batch_embeddings, p=2, dim=1)
                    
                    all_embeddings.append(batch_embeddings.cpu().numpy())
                
                # Concatenate all batches
                embeddings = np.vstack(all_embeddings)
            
            else:
                raise EmbeddingServiceUnavailableError(f"Embedding model '{self.model_name}' is not available")
            
            # Create result list with zero vectors for empty texts
            result = [[0.0] * self.embedding_dim] * len(texts)
            
            # Fill in embeddings for non-empty texts
            for i, idx in enumerate(non_empty_indices):
                result[idx] = embeddings[i].tolist()
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Error generating batch embeddings: {str(e)}")
            raise
    
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
            print(f"[ERROR] Error computing similarity: {str(e)}")
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
