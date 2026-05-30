from pathlib import Path

from backend.app.database import DocumentDatabase


def test_library_revision_changes_when_documents_change(tmp_path: Path):
    database = DocumentDatabase(str(tmp_path / "documents.db"))

    empty_revision = database.get_library_revision(client_id="user-1")
    document = database.create_document(
        filename="stored.pdf",
        original_name="Original.pdf",
        file_size=123,
        file_path=str(tmp_path / "stored.pdf"),
        client_id="user-1",
    )
    created_revision = database.get_library_revision(client_id="user-1")

    assert created_revision != empty_revision

    database.update_document(document.id, client_id="user-1", metadata={"topic": "pricing"})
    updated_revision = database.get_library_revision(client_id="user-1")

    assert updated_revision != created_revision

    database.delete_document(document.id, client_id="user-1")
    deleted_revision = database.get_library_revision(client_id="user-1")

    assert deleted_revision != updated_revision
    assert deleted_revision == empty_revision


def test_search_chunks_bm25_uses_fts_and_tenant_filters(tmp_path: Path):
    database = DocumentDatabase(str(tmp_path / "documents.db"))
    matching_document = database.create_document(
        filename="match.pdf",
        original_name="Match.pdf",
        file_size=10,
        file_path=str(tmp_path / "match.pdf"),
        client_id="user-1",
    )
    other_document = database.create_document(
        filename="other.pdf",
        original_name="Other.pdf",
        file_size=10,
        file_path=str(tmp_path / "other.pdf"),
        client_id="user-2",
    )
    database.store_chunk(
        document_id=matching_document.id,
        chunk_text="pricing renewal clause with exact terms",
        chunk_index=0,
        page_number=2,
    )
    database.store_chunk(
        document_id=other_document.id,
        chunk_text="pricing renewal clause from another tenant",
        chunk_index=0,
        page_number=3,
    )

    results = database.search_chunks_bm25("pricing renewal", limit=5, client_id="user-1")

    assert [result["document_id"] for result in results] == [matching_document.id]
    assert results[0]["chunk_text"] == "pricing renewal clause with exact terms"
    assert results[0]["metadata"]["retrieval_source"] == "bm25"
    assert results[0]["metadata"]["bm25_score"] > 0
    assert results[0]["metadata"]["keyword_score"] == 1.0
