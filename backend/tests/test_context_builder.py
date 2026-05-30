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
