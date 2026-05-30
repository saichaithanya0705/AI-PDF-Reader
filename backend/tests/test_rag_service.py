import importlib
import asyncio
from types import SimpleNamespace

from backend.app.semantic_cache import SemanticCacheContext, SemanticSearchCache


def import_rag_service_with_sqlite(monkeypatch):
    monkeypatch.setenv("USE_SUPABASE", "false")
    return importlib.import_module("backend.app.rag_service")


def test_rag_no_context_does_not_call_llm_for_general_knowledge(monkeypatch):
    rag_module = import_rag_service_with_sqlite(monkeypatch)
    service = object.__new__(rag_module.RAGService)

    async def no_results(**_kwargs):
        return []

    class FailingLLM:
        async def generate_chat_response(self, _messages):
            raise AssertionError("LLM must not be called when retrieval has no context")

    service.search_documents = no_results

    response = asyncio.run(service.generate_rag_response("What is outside the library?", FailingLLM()))

    assert response["has_context"] is False
    assert response["sources"] == []
    assert "uploaded documents" in response["response"]


def test_rag_errors_do_not_leak_internal_exception_details(monkeypatch):
    rag_module = import_rag_service_with_sqlite(monkeypatch)
    service = object.__new__(rag_module.RAGService)

    async def broken_search(**_kwargs):
        raise RuntimeError("database password leaked here")

    service.search_documents = broken_search

    response = asyncio.run(service.generate_rag_response("question", llm_provider=object()))

    assert response["has_context"] is False
    assert response["sources"] == []
    assert "database password leaked here" not in response["response"]
    assert "database password leaked here" not in str(response.get("error", ""))


def test_search_documents_passes_exclude_filter_to_vector_store(monkeypatch):
    rag_module = import_rag_service_with_sqlite(monkeypatch)
    service = object.__new__(rag_module.RAGService)

    class FakeEmbeddingService:
        def generate_embedding(self, query):
            assert query == "find related"
            return [0.1, 0.2]

    class FakeVectorStore:
        def search_similar(self, query_embedding, top_k, document_id=None, exclude_document_id=None, user_id=None):
            assert query_embedding == [0.1, 0.2]
            assert top_k == 4
            assert document_id is None
            assert exclude_document_id == "current-doc"
            assert user_id == "user-1"
            return [
                SimpleNamespace(
                    chunk_text="related chunk",
                    similarity_score=0.9,
                    metadata={},
                )
            ]

    service.embedding_service = FakeEmbeddingService()
    service.vector_store = FakeVectorStore()
    service.cross_encoder = None

    results = asyncio.run(
        service.search_documents(
            query="find related",
            top_k=4,
            exclude_document_id="current-doc",
            user_id="user-1",
            use_advanced_rag=False,
        )
    )

    assert len(results) == 1
    assert results[0].chunk_text == "related chunk"


def test_search_documents_checks_exact_cache_before_database_or_embedding(monkeypatch):
    rag_module = import_rag_service_with_sqlite(monkeypatch)
    service = object.__new__(rag_module.RAGService)
    cache = SemanticSearchCache()
    context = SemanticCacheContext(
        user_id="user-1",
        document_id=None,
        exclude_document_id=None,
        top_k=1,
        use_advanced_rag=False,
        library_revision=cache.revision_for_user("user-1"),
    )
    cache.put(
        "pricing policy",
        [1.0, 0.0],
        context,
        [SimpleNamespace(chunk_text="cached pricing policy", metadata={})],
    )

    class DatabaseMustNotBeTouched:
        def get_library_revision(self, *_args, **_kwargs):
            raise AssertionError("cache hit must happen before SQLite revision lookup")

        def search_chunks_bm25(self, *_args, **_kwargs):
            raise AssertionError("cache hit must happen before BM25 search")

    class EmbeddingMustNotBeTouched:
        def generate_embedding(self, *_args, **_kwargs):
            raise AssertionError("exact cache hit must happen before embedding generation")

    class VectorStoreMustNotBeTouched:
        def search_similar(self, *_args, **_kwargs):
            raise AssertionError("cache hit must happen before vector search")

    monkeypatch.setattr(rag_module, "db", DatabaseMustNotBeTouched())
    service.embedding_service = EmbeddingMustNotBeTouched()
    service.vector_store = VectorStoreMustNotBeTouched()
    service.semantic_cache = cache
    service.cross_encoder = None

    results = asyncio.run(
        service.search_documents(
            query="pricing policy",
            top_k=1,
            user_id="user-1",
            use_advanced_rag=False,
        )
    )

    assert results[0].chunk_text == "cached pricing policy"
    assert results[0].metadata["retrieval_cache_hit_type"] == "exact"


def test_search_documents_merges_bm25_only_candidates(monkeypatch):
    rag_module = import_rag_service_with_sqlite(monkeypatch)
    service = object.__new__(rag_module.RAGService)

    class FakeEmbeddingService:
        def generate_embedding(self, query):
            return [0.1, 0.2]

    class FakeVectorStore:
        def search_similar(self, *_args, **_kwargs):
            return [
                SimpleNamespace(
                    chunk_id="vector-1",
                    document_id="doc-vector",
                    chunk_text="semantic but not keyword focused",
                    chunk_index=0,
                    page_number=1,
                    similarity_score=0.72,
                    metadata={"document_name": "Semantic.pdf"},
                )
            ]

    class FakeDatabase:
        def search_chunks_bm25(self, query, limit, document_id=None, exclude_document_id=None, client_id=None):
            assert query == "pricing renewal"
            assert limit >= 2
            assert document_id is None
            assert exclude_document_id is None
            assert client_id == "user-1"
            return [
                {
                    "chunk_id": "bm25-1",
                    "document_id": "doc-bm25",
                    "chunk_text": "pricing renewal exact keyword match",
                    "chunk_index": 3,
                    "page_number": 7,
                    "client_id": "user-1",
                    "metadata": {
                        "document_name": "Keyword.pdf",
                        "bm25_score": 2.3,
                        "keyword_score": 1.0,
                    },
                }
            ]

    monkeypatch.setattr(rag_module, "db", FakeDatabase())
    service.embedding_service = FakeEmbeddingService()
    service.vector_store = FakeVectorStore()
    service.semantic_cache = SemanticSearchCache()
    service.cross_encoder = None

    results = asyncio.run(
        service.search_documents(
            query="pricing renewal",
            top_k=2,
            user_id="user-1",
            use_advanced_rag=False,
        )
    )

    assert {result.chunk_id for result in results} == {"bm25-1", "vector-1"}
    bm25_result = next(result for result in results if result.chunk_id == "bm25-1")
    assert bm25_result.metadata["retrieval_source"] == "bm25"
    assert bm25_result.metadata["keyword_score"] == 1.0


def test_rank_vector_results_adds_explicit_score_metadata(monkeypatch):
    rag_module = import_rag_service_with_sqlite(monkeypatch)
    service = object.__new__(rag_module.RAGService)

    results = [
        SimpleNamespace(
            chunk_text="pricing terms and renewal limits",
            similarity_score=0.6,
            metadata={"document_name": "Contract.pdf"},
        ),
        SimpleNamespace(
            chunk_text="unrelated appendix",
            similarity_score=0.7,
            metadata={"document_name": "Appendix.pdf"},
        ),
    ]

    ranked = service._rank_vector_results("pricing renewal", results, top_k=2)

    assert ranked[0].chunk_text == "pricing terms and renewal limits"
    assert ranked[0].metadata["vector_similarity"] == 0.6
    assert ranked[0].metadata["lexical_overlap"] == 1.0
    assert ranked[0].metadata["keyword_score"] == 1.0
    assert ranked[0].metadata["bm25_score"] > 0
    assert ranked[0].metadata["retrieval_score"] == 0.68


def test_rank_vector_results_uses_recency_metadata_for_latest_queries(monkeypatch):
    rag_module = import_rag_service_with_sqlite(monkeypatch)
    service = object.__new__(rag_module.RAGService)

    results = [
        SimpleNamespace(
            chunk_text="pricing policy",
            similarity_score=0.9,
            metadata={"document_name": "Old.pdf", "last_uploaded": "2024-01-01T00:00:00"},
        ),
        SimpleNamespace(
            chunk_text="pricing policy",
            similarity_score=0.8,
            metadata={"document_name": "New.pdf", "last_uploaded": "2026-01-01T00:00:00"},
        ),
    ]

    ranked = service._rank_vector_results("latest pricing policy", results, top_k=2)

    assert ranked[0].metadata["document_name"] == "New.pdf"
    assert ranked[0].metadata["recency_intent"] == "latest"
    assert ranked[0].metadata["recency_source"] == "last_uploaded"
    assert ranked[0].metadata["recency_score"] == 1.0


def test_format_retrieval_result_keeps_vector_similarity_distinct_from_rerank(monkeypatch):
    rag_module = import_rag_service_with_sqlite(monkeypatch)

    formatted = rag_module.format_retrieval_result(
        SimpleNamespace(
            chunk_id="chunk-1",
            document_id="doc-1",
            chunk_text="A" * 210,
            page_number=4,
            similarity_score=0.51,
            metadata={
                "document_name": "Source.pdf",
                "section_title": "Important section",
                "vector_similarity": 0.74,
                "retrieval_score": 0.81,
                "rerank_score": 3.25,
            },
        )
    )

    assert formatted["similarity"] == 0.74
    assert formatted["vector_similarity"] == 0.74
    assert formatted["retrieval_score"] == 0.81
    assert formatted["rerank_score"] == 3.25
    assert formatted["section_title"] == "Important section"
    assert formatted["text"].endswith("...")


def test_semantic_cache_exact_hit_skips_embedding_and_vector_search(monkeypatch):
    rag_module = import_rag_service_with_sqlite(monkeypatch)
    monkeypatch.setattr(
        rag_module,
        "db",
        SimpleNamespace(get_library_revision=lambda client_id=None: "rev-1"),
    )
    service = object.__new__(rag_module.RAGService)

    class FakeEmbeddingService:
        def __init__(self):
            self.calls = 0

        def generate_embedding(self, query):
            self.calls += 1
            return [1.0, 0.0]

    class FakeVectorStore:
        def __init__(self):
            self.calls = 0

        def search_similar(self, *_args, **_kwargs):
            self.calls += 1
            return [
                SimpleNamespace(
                    chunk_text="pricing policy",
                    similarity_score=0.9,
                    metadata={"document_name": "Policy.pdf"},
                )
            ]

    service.embedding_service = FakeEmbeddingService()
    service.vector_store = FakeVectorStore()
    service.semantic_cache = SemanticSearchCache()
    service.cross_encoder = None

    first = asyncio.run(service.search_documents("pricing policy", top_k=1, use_advanced_rag=False))
    second = asyncio.run(service.search_documents("pricing policy", top_k=1, use_advanced_rag=False))

    assert first[0].chunk_text == "pricing policy"
    assert second[0].metadata["retrieval_cache_hit"] is True
    assert second[0].metadata["retrieval_cache_hit_type"] == "exact"
    assert service.embedding_service.calls == 1
    assert service.vector_store.calls == 1


def test_semantic_cache_near_duplicate_hit_is_scoped_by_library_revision():
    cache = SemanticSearchCache(similarity_threshold=0.95)
    context = SemanticCacheContext(
        user_id="user-1",
        document_id=None,
        exclude_document_id=None,
        top_k=3,
        use_advanced_rag=False,
        library_revision="rev-1",
    )
    cache.put(
        "pricing renewal",
        [1.0, 0.0],
        context,
        [SimpleNamespace(document_id="doc-1", metadata={})],
    )

    hit = cache.get_semantic([0.99, 0.01], context)

    assert hit is not None
    assert hit[0].metadata["retrieval_cache_hit_type"] == "semantic"
    assert cache.get_semantic(
        [0.99, 0.01],
        SemanticCacheContext(
            user_id="user-1",
            document_id=None,
            exclude_document_id=None,
            top_k=3,
            use_advanced_rag=False,
            library_revision="rev-2",
        ),
    ) is None


def test_semantic_cache_revision_bump_prevents_stale_hits():
    cache = SemanticSearchCache()
    context = SemanticCacheContext(
        user_id="user-1",
        document_id=None,
        exclude_document_id=None,
        top_k=3,
        use_advanced_rag=False,
        library_revision=cache.revision_for_user("user-1"),
    )
    cache.put(
        "pricing renewal",
        [1.0, 0.0],
        context,
        [SimpleNamespace(document_id="doc-1", metadata={})],
    )

    cache.mark_library_changed("user-1")
    changed_context = SemanticCacheContext(
        user_id="user-1",
        document_id=None,
        exclude_document_id=None,
        top_k=3,
        use_advanced_rag=False,
        library_revision=cache.revision_for_user("user-1"),
    )

    assert changed_context.library_revision != context.library_revision
    assert cache.get_exact("pricing renewal", changed_context) is None
