"""NVIDIA-hosted embedding service for the RAG pipeline."""
from __future__ import annotations

import math
from typing import Any, List, Sequence

import requests

from .nvidia_api import NvidiaApiUnavailableError, create_nvidia_api_session, require_nvidia_api_key
from .nvidia_retrieval_config import load_nvidia_embedding_config


class EmbeddingServiceUnavailableError(NvidiaApiUnavailableError):
    """Raised when the NVIDIA embedding service cannot be used safely."""


class EmbeddingService:
    """Generate RAG embeddings through NVIDIA's hosted API."""

    def __init__(self, session: requests.Session | None = None):
        try:
            self.config = load_nvidia_embedding_config()
        except ValueError as exc:
            raise EmbeddingServiceUnavailableError(str(exc)) from exc
        self.model_name = self.config.model_name
        self.embedding_dim = self.config.dimension
        self.base_url = self.config.base_url
        self.timeout_seconds = self.config.timeout_seconds
        try:
            self.api_key = require_nvidia_api_key()
        except NvidiaApiUnavailableError as exc:
            raise EmbeddingServiceUnavailableError(str(exc)) from exc
        self.session = session or create_nvidia_api_session()

    def generate_embedding(self, text: str, input_type: str = "query") -> List[float]:
        """Generate one query or passage embedding without a local-model fallback."""
        if not text or not text.strip():
            return [0.0] * self.embedding_dim
        return self._embed([text], input_type=input_type)[0]

    def generate_embeddings_batch(
        self,
        texts: Sequence[str],
        batch_size: int = 32,
        show_progress: bool = False,
        input_type: str = "passage",
    ) -> List[List[float]]:
        """Generate passage embeddings in batches while retaining input order."""
        del show_progress  # The hosted API has no local progress bar.
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not texts:
            return []

        results: List[List[float]] = [[0.0] * self.embedding_dim for _ in texts]
        non_empty = [(index, text) for index, text in enumerate(texts) if text and text.strip()]
        for start in range(0, len(non_empty), batch_size):
            batch = non_empty[start : start + batch_size]
            embeddings = self._embed([text for _, text in batch], input_type=input_type)
            for (index, _), embedding in zip(batch, embeddings):
                results[index] = embedding
        return results

    def _embed(self, inputs: Sequence[str], input_type: str) -> List[List[float]]:
        if input_type not in {"query", "passage"}:
            raise ValueError("input_type must be 'query' or 'passage'")
        try:
            response = self.session.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
                json={
                    "input": list(inputs),
                    "model": self.model_name,
                    "input_type": input_type,
                    "encoding_format": "float",
                    "truncate": "END",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            response_status = getattr(exc.response, "status_code", None)
            status_detail = (
                f" (HTTP {response_status})"
                if isinstance(response_status, int)
                else ""
            )
            raise EmbeddingServiceUnavailableError(
                f"NVIDIA embedding API request failed{status_detail}"
            ) from exc

        try:
            payload: Any = response.json()
            data = payload["data"]
            ordered = sorted(data, key=lambda item: item["index"])
            if [item["index"] for item in ordered] != list(range(len(inputs))):
                raise ValueError("response indexes do not match request inputs")
            embeddings = [item["embedding"] for item in ordered]
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbeddingServiceUnavailableError(
                "NVIDIA embedding API returned an invalid response"
            ) from exc

        if len(embeddings) != len(inputs):
            raise EmbeddingServiceUnavailableError(
                "NVIDIA embedding API returned an unexpected number of embeddings"
            )
        for embedding in embeddings:
            if not isinstance(embedding, list) or len(embedding) != self.embedding_dim:
                raise EmbeddingServiceUnavailableError(
                    "NVIDIA embedding API returned an unexpected embedding dimension"
                )
            if not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                for value in embedding
            ):
                raise EmbeddingServiceUnavailableError(
                    "NVIDIA embedding API returned invalid embedding values"
                )
        return embeddings

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity for two embedding vectors."""
        if len(embedding1) != len(embedding2) or not embedding1:
            return 0.0
        numerator = sum(left * right for left, right in zip(embedding1, embedding2))
        left_norm = sum(value * value for value in embedding1) ** 0.5
        right_norm = sum(value * value for value in embedding2) ** 0.5
        if not left_norm or not right_norm:
            return 0.0
        return float(max(0.0, min(1.0, numerator / (left_norm * right_norm))))


_embedding_service_instance: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get the process-wide NVIDIA embedding service."""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance


def generate_embedding(text: str) -> List[float]:
    return get_embedding_service().generate_embedding(text)


def generate_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    return get_embedding_service().generate_embeddings_batch(texts, batch_size)
