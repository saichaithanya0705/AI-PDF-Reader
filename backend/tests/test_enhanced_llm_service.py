import json
import asyncio

from backend.app import enhanced_llm_service


def test_related_sections_rejects_negative_llm_section_ids(monkeypatch):
    monkeypatch.setattr(enhanced_llm_service, "CHAT_LLM_AVAILABLE", True)
    monkeypatch.setattr(
        enhanced_llm_service,
        "get_llm_response",
        lambda _messages: json.dumps(
            [
                {
                    "section_id": -1,
                    "relevance_score": 0.99,
                    "snippet": "This should not select the final section.",
                    "connection_type": "similar",
                }
            ]
        ),
    )

    service = enhanced_llm_service.EnhancedLLMService()
    results = asyncio.run(service.find_related_sections(
        selected_text="alpha",
        all_sections=[
            {"document_id": "doc-1", "document_name": "First", "content": "alpha", "title": "First", "page": 1},
            {"document_id": "doc-2", "document_name": "Second", "content": "omega", "title": "Second", "page": 2},
        ],
    ))

    assert results == []


def test_related_sections_rejects_non_array_llm_payload(monkeypatch):
    monkeypatch.setattr(enhanced_llm_service, "CHAT_LLM_AVAILABLE", True)
    monkeypatch.setattr(
        enhanced_llm_service,
        "get_llm_response",
        lambda _messages: json.dumps({"section_id": 0, "relevance_score": 1}),
    )

    service = enhanced_llm_service.EnhancedLLMService()
    results = asyncio.run(service.find_related_sections(
        selected_text="alpha",
        all_sections=[{"document_id": "doc-1", "document_name": "First", "content": "alpha"}],
    ))

    assert results == []


def test_generate_insights_bulb_parses_code_fences_and_uses_full_content(monkeypatch):
    import pytest

    monkeypatch.setattr(enhanced_llm_service, "CHAT_LLM_AVAILABLE", True)
    seen_prompts = []

    def fake_llm(messages):
        seen_prompts.append(messages[1]["content"])
        return '```json\n[{"type": "key-takeaway", "title": "Real Insight", "content": "Grounded"}]\n```'

    monkeypatch.setattr(enhanced_llm_service, "get_llm_response", fake_llm)
    long_content = ("intro " * 250) + "MARKER_AFTER_1000_CHARS"

    service = enhanced_llm_service.EnhancedLLMService()
    insights = asyncio.run(service.generate_insights_bulb(long_content, related_sections=[]))

    assert "MARKER_AFTER_1000_CHARS" in seen_prompts[0]
    assert insights[0]["title"] == "Real Insight"


def test_generate_insights_bulb_raises_on_invalid_llm_failure(monkeypatch):
    import pytest

    monkeypatch.setattr(enhanced_llm_service, "CHAT_LLM_AVAILABLE", True)
    monkeypatch.setattr(
        enhanced_llm_service,
        "get_llm_response",
        lambda _messages: "I encountered an issue with the request format.",
    )

    service = enhanced_llm_service.EnhancedLLMService()
    with pytest.raises(RuntimeError):
        asyncio.run(service.generate_insights_bulb("Some PDF content", related_sections=[]))


def test_generate_insights_bulb_extracts_wrapped_json_and_normalizes_types(monkeypatch):
    monkeypatch.setattr(enhanced_llm_service, "CHAT_LLM_AVAILABLE", True)
    wrapped = (
        "Here are the insights:\n"
        '{"insights": ['
        '{"type": "Summary", "title": "Core Takeaway", "content": "Modulators stay below 0.03 dB at 4.2 K."},'
        '{"type": "key_takeaway", "title": "Cryo Benefit", "content": "Thermal drift drops sharply."}'
        "]}\nLet me know if you need more."
    )
    monkeypatch.setattr(enhanced_llm_service, "get_llm_response", lambda _messages: wrapped)

    service = enhanced_llm_service.EnhancedLLMService()
    insights = asyncio.run(service.generate_insights_bulb("Cryogenic modulators", related_sections=[]))

    assert len(insights) == 2
    assert insights[0]["type"] == "key-takeaway"
    assert insights[0]["title"] == "Core Takeaway"
    assert insights[1]["type"] == "key-takeaway"
    assert insights[1]["title"] == "Cryo Benefit"
