from pathlib import Path


MAIN_SOURCE = Path(__file__).resolve().parents[1] / "app" / "main.py"


def read_main() -> str:
    return MAIN_SOURCE.read_text(encoding="utf-8")


def read_endpoint(source: str, route: str, next_route: str) -> str:
    start = source.index(route)
    end = source.index(next_route, start)
    return source[start:end]


def test_podcast_endpoint_does_not_return_demo_audio_on_tts_failure():
    source = read_main()

    assert "fallback_demo" not in source
    assert "demo_podcast.mp3" not in source


def test_chat_endpoint_does_not_return_internal_exception_details():
    source = read_main()

    assert '"error": error_msg' not in source
    assert "Service Error: {error_msg}" not in source


def test_chat_endpoint_does_not_write_raw_user_message_to_debug_log():
    source = read_main()

    assert 'f.write(f"Message: {request.message}' not in source


def test_rag_mutation_endpoints_require_authenticated_user():
    source = read_main()

    assert "async def process_document_for_rag(document_id: str, current_user: dict = Depends(get_current_user))" in source
    assert "async def delete_document_from_rag(document_id: str, current_user: dict = Depends(get_current_user))" in source


def test_recommendations_and_insights_require_authenticated_user_and_no_mock_payloads():
    source = read_main()

    assert "include_cross_document: bool = Query(True, description=\"Include cross-document recommendations\"),\n    current_user: dict = Depends(get_current_user)" in source
    assert "async def get_insights(\n    document_id: str,\n    page: int = Query(1, ge=1),\n    persona: str = Query(None),\n    job: str = Query(None),\n    current_user: dict = Depends(get_current_user)" in source
    assert "return mock insights" not in source.lower()
    assert "Content Metrics" not in source
    assert "llm_error" not in source


def test_recommendations_endpoint_uses_canonical_rag_retrieval():
    source = read_main()
    endpoint = read_endpoint(
        source,
        '@app.get("/api/recommendations/{document_id}")',
        '@app.get("/api/insights/{document_id}")',
    )

    assert "rag_service.search_documents" in endpoint
    assert "exclude_document_id=document_id" in endpoint
    assert "get_page_content" in endpoint
    assert "vector_store.search" not in endpoint
    assert "get_embedding_service" not in endpoint
    assert "Page {page} content for document" not in endpoint
