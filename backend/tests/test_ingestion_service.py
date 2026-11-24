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


def test_process_collection_passes_materialized_local_paths_to_chunk_collection(monkeypatch, tmp_path):
    import asyncio
    from backend.app import ingestion_service as ing_mod

    local_pdf = tmp_path / "materialized.pdf"
    local_pdf.write_bytes(b"%PDF-1.4\n% content\n")

    remote_doc = Document(
        id="doc-remote-1",
        filename="remote.pdf",
        original_name="Remote.pdf",
        upload_date=datetime.now(),
        file_size=local_pdf.stat().st_size,
        file_path="supabase://documents/user-1/doc-remote-1/remote.pdf",
        client_id="user-1",
    )

    captured_paths = []
    updates = []

    class FakeDB:
        def get_document_by_id(self, doc_id, client_id=None):
            return remote_doc if doc_id == remote_doc.id else None

        def update_document(self, doc_id, client_id=None, **kwargs):
            updates.append((doc_id, kwargs))
            return True

        def delete_chunks_by_document(self, *_args, **_kwargs):
            return 0

        def store_chunk(self, **_kwargs):
            return "chunk-1"

    class FakeChunker:
        def chunk_collection(self, documents, persona=None, job=None):
            captured_paths.extend(doc.file_path for doc in documents)
            return [
                DocumentChunk(
                    text="Materialized chunk",
                    page_number=1,
                    chunk_index=0,
                    document_id=remote_doc.id,
                    metadata={"char_count": 18, "word_count": 2},
                )
            ]

    class FakeEmbedder:
        model_name = "nvidia/nemotron-3.5-embed-1b"
        embedding_dim = 2048

        def generate_embeddings_batch(self, texts, **_kwargs):
            return [[0.1] * 4 for _ in texts]

    class FakeVectorStore:
        def remove_document(self, *_args, **_kwargs):
            return None

        def add_documents(self, embeddings, _metadatas):
            return [f"vec-{i}" for i in range(len(embeddings))]

    monkeypatch.setattr(ing_mod, "db", FakeDB())
    monkeypatch.setattr(
        ing_mod,
        "get_document_storage",
        lambda: type("S", (), {"ensure_local": staticmethod(lambda _loc: local_pdf)})(),
    )

    service = object.__new__(DocumentIngestionService)
    service.chunking_service = FakeChunker()
    service.embedding_service = FakeEmbedder()
    service.vector_store = FakeVectorStore()

    result = asyncio.run(service.process_collection([remote_doc.id], user_id="user-1"))

    assert result["success"] is True
    assert captured_paths == [str(local_pdf)]
    assert not any(p.startswith("supabase://") for p in captured_paths)
