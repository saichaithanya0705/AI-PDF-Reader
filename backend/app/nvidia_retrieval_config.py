"""Validated configuration profiles for NVIDIA-hosted RAG retrieval services."""
from __future__ import annotations

import os
from dataclasses import dataclass


# This is the active NVIDIA Build embedding model. Keep the dimension paired
# with the model so get_vector_store() selects a fresh FAISS namespace on any
# future migration instead of opening an incompatible index.
DEFAULT_EMBEDDING_MODEL = "nvidia/nemotron-3-embed-1b"
DEFAULT_EMBEDDING_DIMENSION = 2048
DEFAULT_EMBEDDING_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_RERANK_MODEL = "nvidia/llama-nemotron-rerank-vl-1b-v2"
DEFAULT_RERANK_ENDPOINT = (
    "https://ai.api.nvidia.com/v1/retrieval/"
    "nvidia/llama-nemotron-rerank-vl-1b-v2/reranking"
)


@dataclass(frozen=True)
class NvidiaEmbeddingConfig:
    model_name: str
    dimension: int
    base_url: str
    timeout_seconds: float

    @property
    def index_namespace(self) -> str:
        model_slug = "".join(
            char if char.isalnum() or char in {"-", "_"} else "-"
            for char in self.model_name
        )
        return f"{model_slug}-{self.dimension}"


@dataclass(frozen=True)
class NvidiaRerankerConfig:
    model_name: str
    endpoint: str
    timeout_seconds: float


def _required_text(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    if not value:
        raise ValueError(f"{name} must not be empty")
    return value


def _positive_integer(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _https_endpoint(name: str, default: str) -> str:
    value = _required_text(name, default).rstrip("/")
    if not value.startswith("https://"):
        raise ValueError(f"{name} must use HTTPS")
    return value


def _positive_timeout(name: str, default: float = 30) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive number") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive number")
    return value


def load_nvidia_embedding_config() -> NvidiaEmbeddingConfig:
    return NvidiaEmbeddingConfig(
        model_name=_required_text("NVIDIA_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        dimension=_positive_integer("NVIDIA_EMBEDDING_DIMENSION", DEFAULT_EMBEDDING_DIMENSION),
        base_url=_https_endpoint("NVIDIA_EMBEDDING_BASE_URL", DEFAULT_EMBEDDING_BASE_URL),
        timeout_seconds=_positive_timeout("NVIDIA_EMBEDDING_TIMEOUT_SECONDS"),
    )


def load_nvidia_reranker_config() -> NvidiaRerankerConfig:
    model_name = _required_text("NVIDIA_RERANK_MODEL", DEFAULT_RERANK_MODEL)
    endpoint = _https_endpoint("NVIDIA_RERANK_ENDPOINT", DEFAULT_RERANK_ENDPOINT)
    expected_route = model_name.replace(".", "_")
    if not endpoint.endswith(f"/{expected_route}/reranking"):
        raise ValueError("NVIDIA_RERANK_ENDPOINT must target NVIDIA_RERANK_MODEL")
    return NvidiaRerankerConfig(
        model_name=model_name,
        endpoint=endpoint,
        timeout_seconds=_positive_timeout("NVIDIA_RERANK_TIMEOUT_SECONDS"),
    )
