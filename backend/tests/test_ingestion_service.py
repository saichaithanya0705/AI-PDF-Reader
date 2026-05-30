from datetime import datetime

from backend.app.chunking_service import DocumentChunk
from backend.app.database import Document
from backend.app.ingestion_service import DocumentIngestionService


def test_vector_metadata_uses_single_canonical_schema():
    service = object.__new__(DocumentIngestionService)
    document = Document(
        id="doc-1",
        filename="stored.pdf",
        original_name="Original.pdf",
        upload_date=datetime.now(),
        file_size=123,
        file_path="/tmp/stored.pdf",
        client_id="user-1",
    )
    chunk = DocumentChunk(
        text="important text",
        page_number=3,
        chunk_index=7,
        document_id="doc-1",
        metadata={"section_title": "Important Section"},
    )

    metadata = service._vector_metadata(document, "user-1", chunk, "chunk-1")

    assert metadata["chunk_id"] == "chunk-1"
    assert metadata["document_id"] == "doc-1"
    assert metadata["chunk_text"] == "important text"
    assert metadata["page_number"] == 3
    assert metadata["section_title"] == "Important Section"
    assert metadata["upload_date"] is not None
    assert metadata["last_uploaded"] is not None
    assert "last_opened" in metadata
    assert "last_accessed" in metadata
    assert {"id", "doc_id", "text", "page", "heading", "client_id"}.isdisjoint(metadata)
