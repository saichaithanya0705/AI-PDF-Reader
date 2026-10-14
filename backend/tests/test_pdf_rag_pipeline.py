import asyncio
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.chunking_service import DocumentChunk
from backend.app.database import Document
from backend.app.ingestion_service import DocumentIngestionService
from backend.app.utils import intelligent_pdf_brain, process_pdfs


def test_backfill_requires_explicit_tenant_scope(monkeypatch):
    monkeypatch.setenv("PERSISTENCE_BACKEND", "sqlite")
    script = importlib.import_module("backend.process_documents_for_rag")

    with pytest.raises(ValueError, match="tenant scope"):
        script._get_documents_for_scope()

    with pytest.raises(ValueError, match="tenant scope"):
        script._get_documents_for_scope(client_id="tenant-1", all_tenants=True)


def test_supabase_backfill_rejects_unscoped_all_tenants(monkeypatch):
    script = importlib.import_module("backend.process_documents_for_rag")
    monkeypatch.setattr(script, "persistence_backend", lambda: "supabase")

    with pytest.raises(ValueError, match="require --client-id"):
        script._get_documents_for_scope(all_tenants=True)


def test_backfill_uses_document_client_id_for_rag_user(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSISTENCE_BACKEND", "sqlite")
    script = importlib.import_module("backend.process_documents_for_rag")

    pdf_path = tmp_path / "stored.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    document = SimpleNamespace(
        id="doc-1",
        original_name="Original.pdf",
        file_path=str(pdf_path),
        client_id="tenant-1",
        user_id="stale-user",
    )

    class FakeDB:
        def __init__(self):
            self.requested_client_id = None

        def get_all_documents(self, client_id=None):
            self.requested_client_id = client_id
            return [document]

        def get_chunk_count(self, document_id, client_id=None):
            assert document_id == "doc-1"
            assert client_id == "tenant-1"
            return 0

    class FakeRAG:
        def __init__(self):
            self.calls = []

        async def process_document(self, **kwargs):
            self.calls.append(kwargs)
            return {"success": True, "chunks_created": 1, "embeddings_generated": 1}

        def get_stats(self, user_id=None):
            assert user_id == "tenant-1"
            return {
                "vector_store": {"total_vectors": 1, "num_documents": 1},
                "database": {"total_chunks": 1},
                "embedding": {"model": "fake", "dimension": 3},
            }

    fake_db = FakeDB()
    fake_rag = FakeRAG()
    monkeypatch.setattr(script, "db", fake_db)
    monkeypatch.setattr(script, "get_rag_service", lambda: fake_rag)
    monkeypatch.setattr(
        script,
        "get_document_storage",
        lambda: SimpleNamespace(ensure_local=lambda location: Path(location)),
    )

    asyncio.run(script.process_all_documents(client_id="tenant-1"))

    assert fake_db.requested_client_id == "tenant-1"
    assert fake_rag.calls[0]["user_id"] == "tenant-1"
    assert fake_rag.calls[0]["user_id"] != document.user_id


def test_backfill_materializes_supabase_pdf_through_document_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSISTENCE_BACKEND", "sqlite")
    script = importlib.import_module("backend.process_documents_for_rag")

    local_pdf = tmp_path / "cached.pdf"
    local_pdf.write_bytes(b"%PDF-1.4\n")
    document = SimpleNamespace(
        id="doc-remote",
        original_name="Remote.pdf",
        file_path="supabase://documents/tenant/doc-remote/remote.pdf",
        client_id="tenant-1",
    )

    class FakeDB:
        def get_all_documents(self, client_id=None):
            assert client_id == "tenant-1"
            return [document]

        def get_chunk_count(self, document_id, client_id=None):
            assert document_id == "doc-remote"
            assert client_id == "tenant-1"
            return 0

    class FakeRAG:
        def __init__(self):
            self.calls = []

        async def process_document(self, **kwargs):
            self.calls.append(kwargs)
            return {"success": True, "chunks_created": 1, "embeddings_generated": 1}

        def get_stats(self, user_id=None):
            assert user_id == "tenant-1"
            return {
                "vector_store": {"total_vectors": 1, "num_documents": 1},
                "database": {"total_chunks": 1},
                "embedding": {"model": "fake", "dimension": 3},
            }

    materialized = []
    fake_rag = FakeRAG()
    monkeypatch.setattr(script, "db", FakeDB())
    monkeypatch.setattr(script, "get_rag_service", lambda: fake_rag)
    monkeypatch.setattr(
        script,
        "get_document_storage",
        lambda: SimpleNamespace(
            ensure_local=lambda location: materialized.append(location) or local_pdf,
        ),
    )

    asyncio.run(script.process_all_documents(client_id="tenant-1"))

    assert materialized == [document.file_path]
    assert fake_rag.calls[0]["pdf_path"] == str(local_pdf)


def test_extract_sections_keeps_same_page_heading_content(monkeypatch):
    class FakePage:
        def __init__(self, lines):
            self.lines = lines

        def get_text(self, kind=None):
            if kind == "dict":
                return {
                    "blocks": [
                        {
                            "lines": [
                                {
                                    "bbox": (0, y, 300, y + 10),
                                    "spans": [{"text": text, "bbox": (0, y, 300, y + 10)}],
                                }
                                for text, y in self.lines
                            ]
                        }
                    ]
                }
            return "\n".join(text for text, _ in self.lines)

    class FakeDoc:
        def __init__(self):
            self.pages = [
                FakePage(
                    [
                        ("Alpha", 10),
                        ("Alpha detail that belongs only to alpha.", 30),
                        ("More alpha evidence.", 45),
                        ("Beta", 100),
                        ("Beta detail that belongs only to beta.", 120),
                    ]
                )
            ]
            self.closed = False

        def __len__(self):
            return len(self.pages)

        def __getitem__(self, index):
            return self.pages[index]

        def close(self):
            self.closed = True

    fake_doc = FakeDoc()

    def fake_outline(self, doc, language_patterns=None, include_positions=False):
        assert include_positions is True
        return [
            {"level": "H1", "text": "Alpha", "page": 0, "y_position": 10},
            {"level": "H1", "text": "Beta", "page": 0, "y_position": 100},
        ]

    monkeypatch.setattr(process_pdfs.fitz, "open", lambda _path: fake_doc)
    monkeypatch.setattr(process_pdfs.HighPerformancePDFProcessor, "extract_outline_from_content", fake_outline)

    sections = process_pdfs.extract_sections("fake.pdf", "doc-1")

    assert fake_doc.closed is True
    assert len(sections) == 2
    assert "Alpha detail" in sections[0].content
    assert "Beta" not in sections[0].content
    assert "Beta detail" in sections[1].content


def test_ingestion_failure_cleans_partial_chunks_and_vectors(monkeypatch, tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    document = Document(
        id="doc-1",
        filename="doc.pdf",
        original_name="Doc.pdf",
        upload_date=None,
        file_size=10,
        file_path=str(pdf_path),
        client_id="user-1",
    )

    class FakeDB:
        def __init__(self):
            self.delete_calls = []
            self.updates = []

        def get_document_by_id(self, document_id, client_id=None):
            assert document_id == "doc-1"
            assert client_id == "user-1"
            return document

        def update_document(self, document_id, client_id=None, **kwargs):
            self.updates.append(kwargs)
            return True

        def delete_chunks_by_document(self, document_id, client_id=None):
            assert client_id == "user-1"
            self.delete_calls.append(document_id)
            return 1

    class FakeVectorStore:
        def __init__(self):
            self.remove_calls = []

        def remove_document(self, document_id):
            self.remove_calls.append(document_id)
            return 1

    fake_db = FakeDB()
    fake_vector_store = FakeVectorStore()
    service = object.__new__(DocumentIngestionService)
    service.vector_store = fake_vector_store
    service.chunking_service = SimpleNamespace(
        chunk_document=lambda **_kwargs: [
            DocumentChunk(
                text="searchable partial text",
                page_number=1,
                chunk_index=0,
                document_id="doc-1",
                metadata={"char_count": 23, "word_count": 3},
            )
        ]
    )
    service._persist_chunks = lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("vector write failed"))

    from backend.app import ingestion_service

    monkeypatch.setattr(ingestion_service, "db", fake_db)

    result = asyncio.run(service.process_document("doc-1", "user-1"))

    assert result["success"] is False
    assert fake_db.delete_calls == ["doc-1", "doc-1"]
    assert fake_vector_store.remove_calls == ["doc-1", "doc-1"]
    assert fake_db.updates[-1]["processing_status"] == "failed"


def test_openai_provider_uses_openai_1x_async_client(monkeypatch):
    from backend.app import llm_providers

    class FakeUsage:
        def model_dump(self):
            return {"total_tokens": 7}

    class FakeCompletions:
        def __init__(self):
            self.calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="provider ok"))],
                usage=FakeUsage(),
            )

    class FakeAsyncOpenAI:
        instances = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())
            self.instances.append(self)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setattr(llm_providers, "AsyncOpenAI", FakeAsyncOpenAI)

    provider = llm_providers.OpenAIProvider()
    response = asyncio.run(provider.generate_text("hello", max_tokens=12))

    assert response.content == "provider ok"
    assert response.usage == {"total_tokens": 7}
    assert FakeAsyncOpenAI.instances[0].kwargs == {"api_key": "test-key"}
    assert FakeAsyncOpenAI.instances[0].chat.completions.calls[0]["model"] == "gpt-test"
    assert FakeAsyncOpenAI.instances[0].chat.completions.calls[0]["max_tokens"] == 12


def test_azure_provider_uses_openai_1x_async_azure_client(monkeypatch):
    from backend.app import llm_providers

    class FakeCompletions:
        def __init__(self):
            self.calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message={"content": "azure ok"})],
                usage=None,
            )

    class FakeAsyncAzureOpenAI:
        instances = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())
            self.instances.append(self)

    monkeypatch.setenv("AZURE_OPENAI_KEY", "azure-key")
    monkeypatch.setenv("AZURE_OPENAI_BASE", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_API_VERSION", "2024-02-15-preview")
    monkeypatch.setenv("AZURE_DEPLOYMENT_NAME", "deployment-a")
    monkeypatch.setattr(llm_providers, "AsyncAzureOpenAI", FakeAsyncAzureOpenAI)

    provider = llm_providers.AzureOpenAIProvider()
    response = asyncio.run(provider.generate_text("hello", max_tokens=8))

    assert response.content == "azure ok"
    assert FakeAsyncAzureOpenAI.instances[0].kwargs["azure_endpoint"] == "https://example.openai.azure.com"
    assert FakeAsyncAzureOpenAI.instances[0].chat.completions.calls[0]["model"] == "deployment-a"
    assert "engine" not in FakeAsyncAzureOpenAI.instances[0].chat.completions.calls[0]


def test_gemini_and_spacy_source_hygiene():
    llm_source = Path(llm_providers_path()).read_text(encoding="utf-8")
    brain_source = Path(intelligent_pdf_brain.__file__).read_text(encoding="utf-8")

    assert "openai.ChatCompletion" not in llm_source
    assert "fallback_provider" not in llm_source
    assert "subprocess.run" not in brain_source
    assert "import subprocess" not in brain_source


def test_intelligent_pdf_brain_without_spacy_is_healthy(monkeypatch):
    monkeypatch.setattr(intelligent_pdf_brain, "spacy", None)

    brain = intelligent_pdf_brain.IntelligentPDFBrain()

    assert brain.nlp is None


def llm_providers_path():
    from backend.app import llm_providers

    return llm_providers.__file__
