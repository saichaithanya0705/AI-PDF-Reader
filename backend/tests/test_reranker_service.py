import pytest
import requests

from backend.app import reranker_service
from backend.app.nvidia_retrieval_config import DEFAULT_RERANK_ENDPOINT, DEFAULT_RERANK_MODEL


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
    session = FakeSession(response)
    return reranker_service.NvidiaRerankerService(session=session), session


def test_reranker_uses_nvidia_api_and_sorts_validated_logits(monkeypatch):
    service, session = _service(
        monkeypatch,
        FakeResponse(
            {
                "rankings": [
                    {"index": 0, "logit": 1.25},
                    {"index": 2, "logit": 4.5},
                    {"index": 1, "logit": -0.5},
                ]
            }
        ),
    )

    scores = service.rerank("what changed?", ["first", "second", "third"])

    assert [(score.index, score.logit) for score in scores] == [(2, 4.5), (0, 1.25), (1, -0.5)]
    assert session.calls[0][0][0] == DEFAULT_RERANK_ENDPOINT
    assert session.calls[0][1]["headers"]["Authorization"] == "Bearer test-key"
    assert session.calls[0][1]["json"] == {
        "model": DEFAULT_RERANK_MODEL,
        "query": {"text": "what changed?"},
        "passages": [{"text": "first"}, {"text": "second"}, {"text": "third"}],
        "truncate": "END",
    }


def test_reranker_rejects_duplicate_or_missing_indexes(monkeypatch):
    service, _ = _service(
        monkeypatch,
        FakeResponse({"rankings": [{"index": 0, "logit": 1.0}, {"index": 0, "logit": 0.5}]}),
    )

    with pytest.raises(reranker_service.RerankerServiceUnavailableError, match="unexpected set"):
        service.rerank("question", ["one", "two"])


def test_reranker_fails_closed_when_nvidia_is_unavailable(monkeypatch):
    service, _ = _service(
        monkeypatch,
        FakeResponse({}, status_error=requests.HTTPError("unauthorized")),
    )

    with pytest.raises(reranker_service.RerankerServiceUnavailableError, match="request failed"):
        service.rerank("question", ["passage"])


def test_reranker_requires_the_shared_nvidia_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    with pytest.raises(reranker_service.RerankerServiceUnavailableError, match="NVIDIA_API_KEY"):
        reranker_service.NvidiaRerankerService()


def test_reranker_rejects_an_endpoint_for_a_different_model(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NVIDIA_RERANK_MODEL", "nvidia/not-the-endpoint-model")

    with pytest.raises(reranker_service.RerankerServiceUnavailableError, match="must target"):
        reranker_service.NvidiaRerankerService()
