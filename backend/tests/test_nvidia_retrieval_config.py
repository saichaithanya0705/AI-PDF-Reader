from backend.app.nvidia_retrieval_config import (
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_RERANK_ENDPOINT,
    DEFAULT_RERANK_MODEL,
    load_nvidia_embedding_config,
    load_nvidia_reranker_config,
)


def test_default_embedding_profile_targets_active_hosted_model(monkeypatch):
    monkeypatch.delenv("NVIDIA_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("NVIDIA_EMBEDDING_DIMENSION", raising=False)

    config = load_nvidia_embedding_config()

    assert DEFAULT_EMBEDDING_MODEL == "nvidia/nemotron-3.5-embed-1b"
    assert config.dimension == DEFAULT_EMBEDDING_DIMENSION == 2048
    assert config.index_namespace == "nvidia-nemotron-3-5-embed-1b-2048"


def test_embedding_profile_namespace_changes_with_model_or_dimension(monkeypatch):
    monkeypatch.setenv("NVIDIA_EMBEDDING_MODEL", "nvidia/next-model")
    monkeypatch.setenv("NVIDIA_EMBEDDING_DIMENSION", "1024")

    config = load_nvidia_embedding_config()

    assert config.index_namespace == "nvidia-next-model-1024"


def test_default_reranker_profile_targets_active_hosted_model_and_dot_route(monkeypatch):
    monkeypatch.delenv("NVIDIA_RERANK_MODEL", raising=False)
    monkeypatch.delenv("NVIDIA_RERANK_ENDPOINT", raising=False)

    config = load_nvidia_reranker_config()

    assert DEFAULT_RERANK_MODEL == "nvidia/nemotron-3.5-rerank-8b"
    assert (
        DEFAULT_RERANK_ENDPOINT
        == "https://ai.api.nvidia.com/v1/retrieval/nvidia/nemotron-3.5-rerank-8b/reranking"
    )
    assert config.model_name == DEFAULT_RERANK_MODEL
    assert config.endpoint == DEFAULT_RERANK_ENDPOINT


def test_reranker_accepts_both_literal_dot_and_underscore_routes(monkeypatch):
    monkeypatch.setenv("NVIDIA_RERANK_MODEL", "nvidia/nemotron-3.5-rerank-8b")
    monkeypatch.setenv(
        "NVIDIA_RERANK_ENDPOINT",
        "https://ai.api.nvidia.com/v1/retrieval/nvidia/nemotron-3_5-rerank-8b/reranking",
    )

    config = load_nvidia_reranker_config()
    assert config.endpoint.endswith("/nvidia/nemotron-3_5-rerank-8b/reranking")
