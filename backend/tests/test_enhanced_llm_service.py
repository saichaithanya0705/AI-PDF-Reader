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
