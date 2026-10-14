import pytest
import requests
from types import SimpleNamespace

from backend.app import embedding_service


class FakeResponse:
    def __init__(self, payload, status_error=None):
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def _service(monkeypatch, response):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NVIDIA_EMBEDDING_DIMENSION", "3")
    session = FakeSession(response)
    return embedding_service.EmbeddingService(session=session), session


def test_generate_embedding_uses_nvidia_query_mode(monkeypatch):
    service, session = _service(
        monkeypatch,
        FakeResponse({"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]}),
    )

    assert service.generate_embedding("meaningful text") == [0.1, 0.2, 0.3]
    assert session.calls[0][1]["json"]["input_type"] == "query"
    assert session.calls[0][1]["headers"]["Authorization"] == "Bearer test-key"


def test_batch_generation_uses_nvidia_passage_mode_and_preserves_order(monkeypatch):
    service, session = _service(
        monkeypatch,
        FakeResponse(
            {
                "data": [
                    {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                ]
            }
        ),
    )

    assert service.generate_embeddings_batch(["first", "", "second"], batch_size=2) == [
        [0.1, 0.2, 0.3],
        [0.0, 0.0, 0.0],
        [0.4, 0.5, 0.6],
    ]
    assert session.calls[0][1]["json"]["input_type"] == "passage"


def test_nvidia_api_failures_do_not_fall_back_to_local_model(monkeypatch):
    service, _ = _service(
        monkeypatch,
        FakeResponse({}, status_error=requests.HTTPError("unauthorized")),
    )

    with pytest.raises(embedding_service.EmbeddingServiceUnavailableError):
        service.generate_embeddings_batch(["chunk one"])


def test_nvidia_api_failure_includes_safe_http_status(monkeypatch):
    error = requests.HTTPError("forbidden")
    error.response = SimpleNamespace(status_code=403)
    service, _ = _service(monkeypatch, FakeResponse({}, status_error=error))

    with pytest.raises(
        embedding_service.EmbeddingServiceUnavailableError,
        match=r"HTTP 403",
    ):
        service.generate_embedding("chunk one")


def test_invalid_nvidia_response_indexes_are_rejected(monkeypatch):
    service, _ = _service(
        monkeypatch,
        FakeResponse(
            {
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                    {"index": 0, "embedding": [0.4, 0.5, 0.6]},
                ]
            }
        ),
    )

    with pytest.raises(embedding_service.EmbeddingServiceUnavailableError, match="invalid response"):
        service.generate_embeddings_batch(["first", "second"])


def test_non_finite_nvidia_values_are_rejected(monkeypatch):
    service, _ = _service(
        monkeypatch,
        FakeResponse({"data": [{"index": 0, "embedding": [0.1, float("nan"), 0.3]}]}),
    )

    with pytest.raises(embedding_service.EmbeddingServiceUnavailableError, match="invalid embedding values"):
        service.generate_embedding("meaningful text")


def test_missing_nvidia_key_fails_closed(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    with pytest.raises(embedding_service.EmbeddingServiceUnavailableError, match="NVIDIA_API_KEY"):
        embedding_service.EmbeddingService()


def test_blank_nvidia_key_fails_closed(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "   ")

    with pytest.raises(embedding_service.EmbeddingServiceUnavailableError, match="NVIDIA_API_KEY"):
        embedding_service.EmbeddingService()


def test_default_session_retries_transient_nvidia_api_failures(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")

    service = embedding_service.EmbeddingService()
    retry_policy = service.session.get_adapter("https://").max_retries

    assert retry_policy.total == 2
    assert set(retry_policy.status_forcelist) == {408, 429, 500, 502, 503, 504}
    assert retry_policy.allowed_methods == frozenset({"POST"})
