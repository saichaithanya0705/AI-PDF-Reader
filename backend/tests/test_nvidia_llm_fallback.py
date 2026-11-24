import asyncio
import json

import pytest

from backend.app import chat_with_llm, llm_providers


class _FakeHttpResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self.text}")

    def json(self):
        return self._payload


def test_get_llm_response_supports_direct_nvidia_provider(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeHttpResponse(
            200,
            {"choices": [{"message": {"content": "Grounded NVIDIA answer"}}]},
        )

    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
    monkeypatch.delenv("NVIDIA_CHAT_MODEL", raising=False)
    monkeypatch.setattr("requests.post", fake_post)

    reply = chat_with_llm.get_llm_response([{"role": "user", "content": "Summarize page 1"}])

    assert reply == "Grounded NVIDIA answer"
    assert captured["url"] == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert captured["json"]["model"] == "nvidia/nemotron-3.5-bolt-e4b"
    assert captured["headers"]["Authorization"] == "Bearer nvapi-test-key"


def test_get_llm_response_gemini_falls_back_to_nvidia_and_respects_disable_flag(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
    monkeypatch.delenv("DISABLE_NVIDIA_LLM_FALLBACK", raising=False)

    monkeypatch.setattr(chat_with_llm, "_call_nvidia_chat", lambda messages, **kwargs: "Fallback insight reply")

    reply = chat_with_llm.get_llm_response([{"role": "user", "content": "Extract insights"}])
    assert reply == "Fallback insight reply"

    monkeypatch.setenv("DISABLE_NVIDIA_LLM_FALLBACK", "true")
    with pytest.raises((ValueError, RuntimeError)):
        chat_with_llm.get_llm_response([{"role": "user", "content": "Extract insights"}])


def test_llm_providers_supports_nvidia_provider_factory_and_methods(monkeypatch):
    def fake_post(url, headers=None, timeout=None, **kwargs):
        request_json = kwargs["json"]
        user_text = request_json["messages"][-1]["content"]
        if "Return ONLY valid JSON" in user_text or "Return a JSON array" in user_text:
            content = json.dumps([
                {
                    "type": "key-insight",
                    "title": "Cryogenic Loss",
                    "content": "Insertion loss stays below 0.03 dB.",
                    "relevance": 0.9,
                }
            ])
            return _FakeHttpResponse(200, {"choices": [{"message": {"content": content}}]})
        return _FakeHttpResponse(200, {"choices": [{"message": {"content": "Chat response from NIM"}}]})

    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
    monkeypatch.setattr(llm_providers.requests, "post", fake_post)

    provider = llm_providers.get_llm_provider()
    assert isinstance(provider, llm_providers.NvidiaLLMProvider)

    text_resp = asyncio.run(provider.generate_text("Hello"))
    assert text_resp.content == "Chat response from NIM"

    chat_resp = asyncio.run(provider.generate_chat_response([{"role": "user", "content": "Hi"}]))
    assert chat_resp == "Chat response from NIM"

    insights = asyncio.run(provider.generate_insights("Return ONLY valid JSON insight", "Reader", "Review"))
    assert len(insights) == 1
    assert insights[0]["title"] == "Cryogenic Loss"


def test_gemini_provider_falls_back_to_nvidia_for_text_and_chat(monkeypatch):
    class _FailingModel:
        async def ainvoke(self, _prompt):
            raise RuntimeError("API_KEY_INVALID")

    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
    monkeypatch.delenv("DISABLE_NVIDIA_LLM_FALLBACK", raising=False)
    monkeypatch.setattr(
        llm_providers.requests,
        "post",
        lambda url, headers=None, json=None, timeout=None: _FakeHttpResponse(
            200, {"choices": [{"message": {"content": "NIM backup answer"}}]}
        ),
    )

    provider = llm_providers.GeminiProvider()
    provider.model = _FailingModel()
    provider.fallback_model = _FailingModel()

    assert provider.nvidia_fallback is not None
    assert asyncio.run(provider.generate_text("Test prompt")).content == "NIM backup answer"
    assert asyncio.run(provider.generate_chat_response([{"role": "user", "content": "Hi"}])) == "NIM backup answer"
