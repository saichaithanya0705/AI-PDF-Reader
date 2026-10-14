import faiss
import json
import numpy as np
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .nvidia_retrieval_config import DEFAULT_EMBEDDING_DIMENSION, load_nvidia_embedding_config
from .storage_paths import get_data_dir

@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    chunk_text: str
    chunk_index: int
    page_number: int
    similarity_score: float
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class FAISSVectorStore:
    def __init__(self, index_path="faiss_index.bin", metadata_path="metadata.pkl", dimension=DEFAULT_EMBEDDING_DIMENSION):
        """
        Initialize FAISS vector store with HNSW index for efficient search.
        
        Args:
            index_path: Path to save/load the FAISS index
            metadata_path: Path to save/load metadata
            dimension: Dimension of the configured NVIDIA embedding model.
        """
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.dimension = dimension
        self.metadata = []  # List of dicts to store metadata for each vector
        self.vectors = []  # Raw vectors are required for correct index rebuilds.
        
        # Initialize HNSW index
        # M=32 is a good trade-off between speed and accuracy
        self.index = self._new_index()
        
        # Load existing index if available
        self.load()

    def _new_index(self):
        return faiss.IndexHNSWFlat(self.dimension, 32)

    def _normalize_vectors(self, embeddings: List[List[float]]) -> np.ndarray:
        vectors = np.array(embeddings, dtype="float32")
        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Expected embeddings with dimension {self.dimension}, got shape {vectors.shape}"
            )
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = np.divide(vectors, norms, out=np.zeros_like(vectors), where=norms > 0)
        return vectors

    def _normalize_query_vector(self, query_embedding: List[float]) -> np.ndarray:
        query_vector = self._normalize_vectors([query_embedding])
        if not np.any(query_vector):
            raise ValueError("Query embedding is empty or zero; refusing low-quality vector search")
        return query_vector

    def _distance_to_similarity(self, distance: float) -> float:
        # Used only as a fallback when a stored vector cannot be reconstructed.
        # HNSW and Flat indexes can expose different L2 distance shapes, so the
        # search path computes cosine directly from stored normalized vectors.
        return float(max(0.0, min(1.0, 1.0 - ((distance * distance) / 2.0))))

    def _similarity_for_index(self, query_vector: np.ndarray, metadata_index: int, distance: float) -> float:
        if metadata_index < len(self.vectors):
            stored_vector = np.asarray(self.vectors[metadata_index], dtype="float32")
            if stored_vector.shape == (self.dimension,):
                return float(max(0.0, min(1.0, np.dot(query_vector, stored_vector))))
        return self._distance_to_similarity(distance)

    def _reconstruct_vectors_from_index(self) -> List[List[float]]:
        if self.index.ntotal == 0:
            return []
        try:
            if hasattr(self.index, "reconstruct_n"):
                vectors = self.index.reconstruct_n(0, self.index.ntotal)
                return np.asarray(vectors, dtype="float32").tolist()
            return [
                np.asarray(self.index.reconstruct(i), dtype="float32").tolist()
                for i in range(self.index.ntotal)
            ]
        except Exception as exc:
            raise RuntimeError(
                "Cannot rebuild FAISS index because raw vectors are missing and reconstruction failed"
            ) from exc

    def _ensure_vectors_available(self) -> List[List[float]]:
        if len(self.vectors) == len(self.metadata):
            return self.vectors
        if self.index.ntotal == len(self.metadata):
            self.vectors = self._reconstruct_vectors_from_index()
            return self.vectors
        raise RuntimeError(
            "Vector store metadata and index are out of sync; refusing unsafe partial rebuild"
        )

    def add_documents(self, embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        """
        Add documents to the vector store.
        
        Args:
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries corresponding to embeddings
        """
        if not embeddings:
            return []
        if len(embeddings) != len(metadatas):
            raise ValueError("Embeddings and metadata must have the same length")

        vectors = self._normalize_vectors(embeddings)
        start_index = len(self.metadata)
        
        # Add to FAISS index
        self.index.add(vectors)
        
        # Store metadata
        self.metadata.extend(dict(metadata) for metadata in metadatas)
        self.vectors.extend(vectors.tolist())
        
        # Save to disk
        self.save()
        print(f"[*] Added {len(embeddings)} documents to FAISS index. Total: {self.index.ntotal}")
        return list(range(start_index, start_index + len(embeddings)))

    # Alias for compatibility
    add_embeddings = add_documents

    def remove_document(self, document_id: str) -> int:
        """
        Remove document from index.
        Note: FAISS IndexHNSWFlat doesn't support easy removal by ID without rebuilding.
        This is a simplified implementation that rebuilds the index if needed,
        or just marks metadata as removed (soft delete).
        For now, we will implement a rebuild approach which is slow but correct.
        """
        new_metadata = []
        new_vectors = []
        count = 0

        vectors = self._ensure_vectors_available()
        for item, vector in zip(self.metadata, vectors):
            item_document_id = item.get('document_id') or item.get('doc_id')
            if item_document_id != document_id:
                new_metadata.append(item)
                new_vectors.append(vector)
            else:
                count += 1

        if count == 0:
            return 0

        self.index = self._new_index()
        if new_vectors:
            self.index.add(self._normalize_vectors(new_vectors))
        self.metadata = new_metadata
        self.vectors = new_vectors
        self.save()
        return count

    def search(self, query_embedding: List[float], k: int = 5, filter_criteria: Dict = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            filter_criteria: Optional dictionary to filter results (e.g. {'user_id': '123'})
            
        Returns:
            List of metadata dictionaries with 'score' added
        """
        if self.index.ntotal == 0 or k <= 0:
            return []
            
        query_vector = self._normalize_query_vector(query_embedding)

        max_search_k = min(self.index.ntotal, len(self.metadata))
        if max_search_k <= 0:
            return []
        search_k = min(max_search_k, max(k, k * 5 if filter_criteria else k))

        while search_k <= max_search_k:
            distances, indices = self.index.search(query_vector, search_k)
            results = []

            for i, idx in enumerate(indices[0]):
                if idx == -1 or idx >= len(self.metadata):
                    continue

                item = self.metadata[idx]
                if filter_criteria and not self._metadata_matches(item, filter_criteria):
                    continue

                distance = float(distances[0][i])
                result = item.copy()
                result['vector_distance'] = distance
                result['score'] = self._similarity_for_index(query_vector[0], idx, distance)
                results.append(result)

                if len(results) >= k:
                    return results

            if search_k == max_search_k:
                return results

            search_k = min(max_search_k, max(search_k + 1, search_k * 2))

        return []

    def _metadata_matches(self, item: Dict[str, Any], filter_criteria: Dict[str, Any]) -> bool:
        for key, value in filter_criteria.items():
            item_value = item.get(key)
            if key == 'document_id' and item_value is None:
                item_value = item.get('doc_id')
            if key == 'exclude_doc_id':
                if (item.get('document_id') or item.get('doc_id')) == value:
                    return False
                continue
            if item_value != value:
                return False

        return True

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: str = None,
        user_id: str = None,
        exclude_document_id: str = None,
    ) -> List[SearchResult]:
        """
        Search for similar documents and return SearchResult objects
        """
        filter_criteria = {}
        if document_id:
            filter_criteria['document_id'] = document_id
        if user_id:
            filter_criteria['user_id'] = user_id
        if exclude_document_id:
            filter_criteria['exclude_doc_id'] = exclude_document_id
            
        results_data = self.search(query_embedding, k=top_k, filter_criteria=filter_criteria)
        
        # Convert to SearchResult objects
        search_results = []
        for item in results_data:
            metadata = dict(item.get('metadata') or {})
            for key in ('document_name', 'filename', 'section_title', 'heading'):
                if key in item and key not in metadata:
                    metadata[key] = item[key]
            if 'vector_distance' in item:
                metadata['vector_distance'] = item['vector_distance']

            search_results.append(SearchResult(
                chunk_id=item.get('chunk_id') or item.get('id', ''),
                document_id=item.get('document_id') or item.get('doc_id', ''),
                chunk_text=item.get('chunk_text') or item.get('text', ''),
                chunk_index=item.get('chunk_index', 0),
                page_number=item.get('page_number') or item.get('page', 0),
                similarity_score=item.get('score', 0.0),
                user_id=item.get('user_id'),
                metadata=metadata
            ))
            
        return search_results

    def _metadata_json_path(self) -> str:
        if self.metadata_path.endswith(".pkl"):
            return self.metadata_path[:-4] + ".json"
        if self.metadata_path.endswith(".json"):
            return self.metadata_path
        return self.metadata_path + ".json"

    def save(self):
        """Save index and metadata to disk (metadata as JSON)."""
        try:
            faiss.write_index(self.index, self.index_path)
            json_path = self._metadata_json_path()
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "metadata": self.metadata,
                        "vectors": self.vectors,
                        "dimension": self.dimension,
                    },
                    f,
                )
        except Exception as e:
            print(f"[ERROR] Failed to save FAISS index: {str(e)}")

    def load(self):
        """Load index and metadata from disk. Legacy pickle metadata is refused."""
        json_path = self._metadata_json_path()
        if os.path.exists(self.index_path) and os.path.exists(json_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(json_path, encoding="utf-8") as f:
                    payload = json.load(f)
                if isinstance(payload, list):
                    self.metadata = payload
                    self.vectors = self._reconstruct_vectors_from_index()
                    self.save()
                else:
                    self.metadata = payload.get("metadata", [])
                    self.vectors = payload.get("vectors", [])
                    if len(self.vectors) != len(self.metadata):
                        self.vectors = self._reconstruct_vectors_from_index()
                print(f"[*] Loaded FAISS index with {self.index.ntotal} vectors")
            except Exception as e:
                print(f"[ERROR] Failed to load FAISS index: {str(e)}")
                self.index = self._new_index()
                self.metadata = []
                self.vectors = []
        elif os.path.exists(self.metadata_path) and self.metadata_path.endswith(".pkl"):
            print("[WARNING] Ignoring legacy pickle metadata; rebuild the vector store from source chunks.")
    
    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get vector store statistics"""
        del user_id  # Local FAISS statistics are not partitioned by tenant.
        return {
            'total_vectors': self.index.ntotal,
            'num_documents': len(set((m.get('document_id') or m.get('doc_id')) for m in self.metadata)) if self.metadata else 0,
            'index_type': "HNSW"
        }

# Global instance
_vector_store_instance = None


def get_vector_store():
    global _vector_store_instance
    if _vector_store_instance is None:
        from .persistence import db, persistence_backend

        if persistence_backend() == "supabase":
            from .supabase_vector_store import SupabaseVectorStore

            _vector_store_instance = SupabaseVectorStore(db)
            return _vector_store_instance

        config = load_nvidia_embedding_config()
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        index_path = data_dir / f"faiss_index-{config.index_namespace}.bin"
        metadata_path = data_dir / f"metadata-{config.index_namespace}.json"
        _vector_store_instance = FAISSVectorStore(
            str(index_path),
            str(metadata_path),
            dimension=config.dimension,
        )
    return _vector_store_instance
