import asyncio
from types import SimpleNamespace

from backend.app import context_builder


class FakeRAGService:
    def __init__(self):
        self.calls = []

    async def search_documents(self, **kwargs):
        self.calls.append(kwargs)
        return [
            SimpleNamespace(
                chunk_id="chunk-1",
                document_id="doc-2",
                chunk_text="This is a related chunk from another PDF.",
                page_number=3,
                similarity_score=0.82,
                metadata={
                    "document_name": "Related.pdf",
                    "vector_similarity": 0.82,
                    "retrieval_score": 0.86,
                    "lexical_overlap": 0.4,
                },
            )
        ]


def test_library_search_uses_canonical_rag_service(monkeypatch):
    fake_service = FakeRAGService()

    import backend.app.rag_service as rag_service

    monkeypatch.setattr(rag_service, "get_rag_service", lambda: fake_service)

    results = asyncio.run(
        context_builder.search_library_documents(
            query_text="search query",
            user_id="user-1",
            top_k=2,
        )
    )

    assert fake_service.calls == [
        {
            "query": "search query",
            "top_k": 2,
            "user_id": "user-1",
            "use_advanced_rag": False,
        }
    ]
    assert results[0]["document_name"] == "Related.pdf"
    assert results[0]["page_number"] == 3
    assert results[0]["similarity"] == 0.82
    assert results[0]["vector_similarity"] == 0.82
    assert results[0]["retrieval_score"] == 0.86


def test_related_search_excludes_current_document_through_rag_service(monkeypatch):
    fake_service = FakeRAGService()

    import backend.app.rag_service as rag_service

    monkeypatch.setattr(rag_service, "get_rag_service", lambda: fake_service)

    results = asyncio.run(
        context_builder.search_related_documents(
            db=object(),
            query_text="current page text",
            current_doc_id="doc-1",
            user_id="user-1",
            top_k=3,
        )
    )

    assert fake_service.calls == [
        {
            "query": "current page text",
            "top_k": 3,
            "exclude_document_id": "doc-1",
            "user_id": "user-1",
            "use_advanced_rag": False,
        }
    ]
    assert results[0]["document_id"] == "doc-2"
    assert results[0]["lexical_overlap"] == 0.4


def test_build_library_context_handles_mixed_timezone_upload_dates():
    from datetime import datetime, timezone

    docs = [
        SimpleNamespace(
            id="doc-aware",
            original_name="Aware.pdf",
            filename="aware.pdf",
            upload_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
            file_size=1024,
            status="processed",
            metadata={"page_count": 4},
        ),
        SimpleNamespace(
            id="doc-none",
            original_name="None.pdf",
            filename="none.pdf",
            upload_date=None,
            file_size=512,
            status="uploaded",
            metadata={},
        ),
    ]
    fake_db = SimpleNamespace(get_all_documents=lambda client_id=None: docs)

    context = asyncio.run(context_builder.build_library_context(fake_db, "user-1"))

    assert context["statistics"]["total_documents"] == 2
    assert context["document_summaries"][0]["id"] == "doc-aware"
    assert context["document_summaries"][0]["pages"] == 4


def test_build_enriched_messages_includes_library_search_results():
    context = {
        "type": "library",
        "system_instruction": "Library assistant",
        "statistics": {"total_documents": 2, "total_size_mb": 1.2},
        "search_results": [
            {
                "document_id": "doc-1",
                "document_name": "Cryogenics.pdf",
                "page_number": 2,
                "text": "Liquid helium maintains 4.2 K cooling loops.",
            }
        ],
    }

    messages = context_builder.build_enriched_messages(
        user_message="What maintains 4.2 K cooling?",
        context=context,
        conversation_history=[],
    )

    last_user_content = messages[-1]["content"]
    assert "Cryogenics.pdf" in last_user_content
    assert "Liquid helium maintains 4.2 K cooling loops." in last_user_content
