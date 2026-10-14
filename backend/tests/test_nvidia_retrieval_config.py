from backend.app.nvidia_retrieval_config import (
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_EMBEDDING_MODEL,
    load_nvidia_embedding_config,
)


def test_default_embedding_profile_targets_active_hosted_model(monkeypatch):
    monkeypatch.delenv("NVIDIA_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("NVIDIA_EMBEDDING_DIMENSION", raising=False)

    config = load_nvidia_embedding_config()

    assert DEFAULT_EMBEDDING_MODEL == "nvidia/nemotron-3-embed-1b"
    assert config.dimension == DEFAULT_EMBEDDING_DIMENSION == 2048
    assert config.index_namespace == "nvidia-nemotron-3-embed-1b-2048"


def test_embedding_profile_namespace_changes_with_model_or_dimension(monkeypatch):
    monkeypatch.setenv("NVIDIA_EMBEDDING_MODEL", "nvidia/next-model")
    monkeypatch.setenv("NVIDIA_EMBEDDING_DIMENSION", "1024")

    config = load_nvidia_embedding_config()

    assert config.index_namespace == "nvidia-next-model-1024"
