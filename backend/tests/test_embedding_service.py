import pytest

from backend.app import embedding_service


def test_generate_embedding_raises_when_no_model_loaded():
    service = embedding_service.EmbeddingService.__new__(embedding_service.EmbeddingService)
    service.model_name = "test-model"
    service.embedding_dim = 3
    service.model = None
    service.transformers_model = None
    service.use_transformers_fallback = False
    service.load_error = RuntimeError("model failed to load")

    with pytest.raises(embedding_service.EmbeddingServiceUnavailableError):
        service.generate_embedding("meaningful text")


def test_batch_generation_raises_instead_of_returning_fake_zero_vectors():
    service = embedding_service.EmbeddingService.__new__(embedding_service.EmbeddingService)
    service.model_name = "test-model"
    service.embedding_dim = 3
    service.model = None
    service.transformers_model = None
    service.use_transformers_fallback = False
    service.load_error = RuntimeError("model failed to load")

    with pytest.raises(embedding_service.EmbeddingServiceUnavailableError):
        service.generate_embeddings_batch(["chunk one", "chunk two"])


def test_batch_generation_propagates_model_errors():
    class FailingModel:
        def encode(self, *_args, **_kwargs):
            raise RuntimeError("encoder exploded")

    service = embedding_service.EmbeddingService.__new__(embedding_service.EmbeddingService)
    service.model_name = "test-model"
    service.embedding_dim = 3
    service.model = FailingModel()
    service.transformers_model = None
    service.use_transformers_fallback = False
    service.load_error = None

    with pytest.raises(RuntimeError, match="encoder exploded"):
        service.generate_embeddings_batch(["chunk one"])
