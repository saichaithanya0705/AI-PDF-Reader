from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.app import document_storage
from backend.app.document_storage import SupabaseDocumentStorage
from backend.app.supabase_database import SupabaseDatabase


class _Query:
    def __init__(self, data=None, count=None):
        self.response = SimpleNamespace(data=data or [], count=count)

    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: self

    def execute(self):
        return self.response


class _DatabaseClient:
    def __init__(self, *, table_data=None, rpc_data=None):
        self.table_query = _Query(table_data)
        self.rpc_query = _Query(rpc_data)
        self.rpc_name = None
        self.rpc_params = None

    def table(self, _name):
        return self.table_query

    def rpc(self, name, params):
        self.rpc_name = name
        self.rpc_params = params
        return self.rpc_query


def _database(client):
    database = object.__new__(SupabaseDatabase)
    database.client = client
    return database


@pytest.mark.parametrize(
    "operation",
    [
        lambda database: database.get_all_documents(),
        lambda database: database.get_document_by_id(str(uuid4())),
        lambda database: database.get_chunks_by_document(str(uuid4())),
        lambda database: database.get_chunk_count(),
    ],
)
def test_service_role_document_reads_fail_closed_without_tenant(operation):
    with pytest.raises(ValueError, match="tenant user ID"):
        operation(_database(_DatabaseClient()))


def test_supabase_document_metadata_matches_reader_contract():
    user_id = str(uuid4())
    client = _DatabaseClient(
        table_data=[
            {
                "id": str(uuid4()),
                "document_id": str(uuid4()),
                "chunk_text": "Page content",
                "chunk_index": 0,
                "page_number": 3,
                "metadata": {},
            }
        ]
    )

    metadata = _database(client).get_document_metadata(str(uuid4()), client_id=user_id)

    assert metadata == [
        {"page": 3, "text": "Page content", "embedding_vector": None}
    ]


def test_supabase_bm25_rows_expose_hybrid_retrieval_metadata():
    user_id = str(uuid4())
    client = _DatabaseClient(
        rpc_data=[
            {
                "chunk_id": str(uuid4()),
                "document_id": str(uuid4()),
                "chunk_text": "pricing renewal",
                "chunk_index": 0,
                "page_number": 1,
                "client_id": user_id,
                "filename": "stored.pdf",
                "original_name": "Pricing.pdf",
                "file_path": f"supabase://documents/{user_id}/doc/stored.pdf",
                "upload_date": "2026-09-13T00:00:00Z",
                "bm25_score": 0.75,
                "metadata": {"chunk_id": "chunk-1"},
            }
        ]
    )

    rows = _database(client).search_chunks_bm25(
        "pricing", client_id=user_id
    )

    assert client.rpc_name == "search_document_chunks_fts"
    assert client.rpc_params["filter_user_id"] == user_id
    assert rows[0]["metadata"]["document_name"] == "Pricing.pdf"
    assert rows[0]["metadata"]["retrieval_source"] == "bm25"
    assert rows[0]["metadata"]["keyword_score"] == 1.0


class _Bucket:
    def __init__(self):
        self.uploaded = None
        self.removed = None

    def upload(self, key, content, options):
        self.uploaded = (key, content, options)

    def remove(self, keys):
        self.removed = keys


class _StorageClient:
    def __init__(self, bucket):
        self.bucket = bucket
        self.storage = self

    def from_(self, name):
        assert name == "documents"
        return self.bucket


def _storage(bucket):
    storage = object.__new__(SupabaseDocumentStorage)
    storage.bucket = "documents"
    storage.client = _StorageClient(bucket)
    return storage


def test_supabase_storage_uses_tenant_document_key_and_local_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(document_storage, "DOCS_DIR", tmp_path)
    bucket = _Bucket()
    storage = _storage(bucket)
    user_id = str(uuid4())
    document_id = str(uuid4())

    location = storage.store_pdf(
        user_id=user_id,
        document_id=document_id,
        filename="stored.pdf",
        content=b"%PDF-1.4\n",
    )

    assert location == f"supabase://documents/{user_id}/{document_id}/stored.pdf"
    assert bucket.uploaded[0] == f"{user_id}/{document_id}/stored.pdf"
    assert storage.ensure_local(location).read_bytes() == b"%PDF-1.4\n"

    storage.delete(location)

    assert bucket.removed == [f"{user_id}/{document_id}/stored.pdf"]
    assert not storage._cache_path(f"{user_id}/{document_id}/stored.pdf").exists()


def test_supabase_storage_rejects_untrusted_identity_and_bucket():
    storage = _storage(_Bucket())

    with pytest.raises(ValueError, match="user_id must be a UUID"):
        storage.store_pdf(
            user_id="../another-user",
            document_id=str(uuid4()),
            filename="stored.pdf",
            content=b"%PDF-1.4\n",
        )

    with pytest.raises(ValueError, match="unexpected bucket"):
        storage.ensure_local(
            f"supabase://other/{uuid4()}/{uuid4()}/stored.pdf"
        )


class _RankedChunkClient:
    """Fake pgvector RPC that applies filters and LIMIT server-side, like Postgres."""

    def __init__(self, rows, *, supports_exclude=True):
        self.rows = rows
        self.supports_exclude = supports_exclude
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, dict(params)))
        if "exclude_document_id" in params and not self.supports_exclude:
            raise RuntimeError("Could not find the function public.match_document_chunks")
        rows = [
            row for row in self.rows
            if (params.get("filter_document_id") is None or row["document_id"] == params["filter_document_id"])
            and row["document_id"] != params.get("exclude_document_id")
        ]
        return _Query(rows[: params["match_count"]])


def _ranked_chunk_rows(current_doc, other_doc, current_count=10):
    rows = [
        {
            "id": str(uuid4()),
            "document_id": current_doc,
            "chunk_text": f"current page chunk {index}",
            "chunk_index": index,
            "page_number": 1,
            "similarity": 0.99 - index * 0.001,
            "metadata": {},
        }
        for index in range(current_count)
    ]
    rows.append(
        {
            "id": str(uuid4()),
            "document_id": other_doc,
            "chunk_text": "related content in another pdf",
            "chunk_index": 0,
            "page_number": 4,
            "similarity": 0.5,
            "metadata": {},
        }
    )
    return rows


@pytest.mark.parametrize("supports_exclude", [True, False])
def test_supabase_cross_document_search_excludes_before_limit(supports_exclude):
    from backend.app.supabase_vector_store import SupabaseVectorStore

    user_id, current_doc, other_doc = str(uuid4()), str(uuid4()), str(uuid4())
    client = _RankedChunkClient(
        _ranked_chunk_rows(current_doc, other_doc), supports_exclude=supports_exclude
    )

    results = SupabaseVectorStore(_database(client)).search_similar(
        [0.1, 0.2], top_k=3, user_id=user_id, exclude_document_id=current_doc
    )

    assert [result.document_id for result in results] == [other_doc]
    assert results[0].page_number == 4
