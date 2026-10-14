import importlib
import json
import sys
import types
from pathlib import Path

from backend.app.vector_store import FAISSVectorStore


def test_remove_document_rebuilds_index_and_removed_document_is_not_searchable(tmp_path: Path):
    store = FAISSVectorStore(
        index_path=str(tmp_path / "index.faiss"),
        metadata_path=str(tmp_path / "metadata.json"),
        dimension=2,
    )

    added_indices = store.add_documents(
        embeddings=[[1.0, 0.0], [0.0, 1.0], [0.8, 0.2]],
        metadatas=[
            {"chunk_id": "a1", "document_id": "doc-a", "chunk_text": "alpha", "chunk_index": 0, "page_number": 1},
            {"chunk_id": "b1", "document_id": "doc-b", "chunk_text": "bravo", "chunk_index": 0, "page_number": 1},
            {"chunk_id": "a2", "document_id": "doc-a", "chunk_text": "alpha followup", "chunk_index": 1, "page_number": 2},
        ],
    )

    assert added_indices == [0, 1, 2]
    assert store.remove_document("doc-a") == 2

    results = store.search([1.0, 0.0], k=3)

    assert [result["document_id"] for result in results] == ["doc-b"]
    assert store.index.ntotal == 1
    assert store.get_stats(user_id="tenant-1")["num_documents"] == 1


def test_vector_store_metadata_json_does_not_load_legacy_pickle(tmp_path: Path):
    index_path = tmp_path / "index.faiss"
    metadata_path = tmp_path / "metadata.pkl"
    store = FAISSVectorStore(str(index_path), str(metadata_path), dimension=2)
    store.add_documents(
        embeddings=[[1.0, 0.0]],
        metadatas=[{"chunk_id": "a1", "document_id": "doc-a", "chunk_text": "alpha", "chunk_index": 0, "page_number": 1}],
    )

    json_path = Path(str(metadata_path)[:-4] + ".json")
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert "metadata" in payload
    assert "vectors" in payload
    assert not metadata_path.exists()


def test_search_similar_can_exclude_current_document(tmp_path: Path):
    store = FAISSVectorStore(
        index_path=str(tmp_path / "index.faiss"),
        metadata_path=str(tmp_path / "metadata.json"),
        dimension=2,
    )
    store.add_documents(
        embeddings=[[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
        metadatas=[
            {"chunk_id": "a1", "document_id": "current-doc", "chunk_text": "current", "chunk_index": 0, "page_number": 1, "user_id": "u1"},
            {"chunk_id": "b1", "document_id": "related-doc", "chunk_text": "related", "chunk_index": 0, "page_number": 1, "user_id": "u1"},
            {"chunk_id": "c1", "document_id": "other-user", "chunk_text": "other", "chunk_index": 0, "page_number": 1, "user_id": "u2"},
        ],
    )

    results = store.search_similar(
        [1.0, 0.0],
        top_k=3,
        user_id="u1",
        exclude_document_id="current-doc",
    )

    assert [result.document_id for result in results] == ["related-doc"]


def test_search_similarity_score_is_high_for_nearest_vector(tmp_path: Path):
    store = FAISSVectorStore(
        index_path=str(tmp_path / "index.faiss"),
        metadata_path=str(tmp_path / "metadata.json"),
        dimension=2,
    )
    store.add_documents(
        embeddings=[[10.0, 0.0], [0.0, 5.0]],
        metadatas=[
            {"chunk_id": "exact", "document_id": "doc-a", "chunk_text": "exact", "chunk_index": 0, "page_number": 1},
            {"chunk_id": "orthogonal", "document_id": "doc-b", "chunk_text": "orthogonal", "chunk_index": 0, "page_number": 1},
        ],
    )

    results = store.search_similar([2.0, 0.0], top_k=2)

    assert results[0].chunk_id == "exact"
    assert results[0].similarity_score > 0.99
    assert results[1].similarity_score < 0.01
    assert "vector_distance" in results[0].metadata


def test_filtered_search_expands_candidates_until_matching_tenant_is_found(tmp_path: Path):
    store = FAISSVectorStore(
        index_path=str(tmp_path / "index.faiss"),
        metadata_path=str(tmp_path / "metadata.json"),
        dimension=2,
    )
    embeddings = [[1.0, 0.0] for _ in range(12)] + [[0.0, 1.0]]
    metadatas = [
        {
            "chunk_id": f"other-{index}",
            "document_id": f"other-doc-{index}",
            "chunk_text": "other user text",
            "chunk_index": 0,
            "page_number": 1,
            "user_id": "other-user",
        }
        for index in range(12)
    ]
    metadatas.append(
        {
            "chunk_id": "target",
            "document_id": "target-doc",
            "chunk_text": "target user text",
            "chunk_index": 0,
            "page_number": 1,
            "user_id": "target-user",
        }
    )
    store.add_documents(embeddings=embeddings, metadatas=metadatas)

    results = store.search_similar([1.0, 0.0], top_k=1, user_id="target-user")

    assert [result.chunk_id for result in results] == ["target"]


def test_global_vector_store_uses_shared_nvidia_embedding_profile(monkeypatch, tmp_path: Path):
    from backend.app import vector_store

    captured = {}

    class CapturingStore:
        def __init__(self, index_path, metadata_path, dimension):
            captured.update(
                index_path=index_path,
                metadata_path=metadata_path,
                dimension=dimension,
            )

    monkeypatch.setenv("NVIDIA_EMBEDDING_MODEL", "nvidia/test-embedding")
    monkeypatch.setenv("NVIDIA_EMBEDDING_DIMENSION", "3")
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PERSISTENCE_BACKEND", "sqlite")
    monkeypatch.setattr(vector_store, "FAISSVectorStore", CapturingStore)
    monkeypatch.setattr(vector_store, "_vector_store_instance", None)

    vector_store.get_vector_store()

    assert captured["dimension"] == 3
    assert Path(captured["index_path"]) == tmp_path / "faiss_index-nvidia-test-embedding-3.bin"
    assert Path(captured["metadata_path"]) == tmp_path / "metadata-nvidia-test-embedding-3.json"


def test_global_vector_store_uses_supabase_adapter_for_supabase_persistence(monkeypatch):
    from backend.app import persistence, vector_store

    captured = {}

    class CapturingSupabaseStore:
        def __init__(self, database):
            captured["database"] = database

    fake_database = object()
    fake_module = types.ModuleType("backend.app.supabase_vector_store")
    fake_module.SupabaseVectorStore = CapturingSupabaseStore
    monkeypatch.setenv("PERSISTENCE_BACKEND", "supabase")
    monkeypatch.setattr(persistence, "db", fake_database)
    monkeypatch.setitem(sys.modules, "backend.app.supabase_vector_store", fake_module)
    monkeypatch.setattr(vector_store, "_vector_store_instance", None)

    store = vector_store.get_vector_store()

    assert isinstance(store, CapturingSupabaseStore)
    assert captured["database"] is fake_database


def test_supabase_vector_stats_require_and_forward_tenant_scope(monkeypatch):
    database_module = types.ModuleType("backend.app.supabase_database")
    database_module.SupabaseDatabase = object
    monkeypatch.setitem(sys.modules, "backend.app.supabase_database", database_module)
    monkeypatch.delitem(sys.modules, "backend.app.supabase_vector_store", raising=False)
    supabase_vector_store = importlib.import_module("backend.app.supabase_vector_store")

    class FakeDatabase:
        def __init__(self):
            self.requested_client_id = None

        def _require_user_id(self, user_id):
            assert user_id == "tenant-1"
            return "validated-tenant-1"

        def get_chunk_count(self, client_id=None):
            self.requested_client_id = client_id
            return 7

    database = FakeDatabase()
    store = supabase_vector_store.SupabaseVectorStore(database)

    stats = store.get_stats(user_id="tenant-1")

    assert stats["total_vectors"] == 7
    assert database.requested_client_id == "validated-tenant-1"


def test_app_data_dir_defaults_to_backend_data(monkeypatch):
    from backend.app import storage_paths

    monkeypatch.delenv("APP_DATA_DIR", raising=False)

    assert storage_paths.get_data_dir() == Path(storage_paths.__file__).resolve().parents[1] / "data"


def test_relative_app_data_dir_is_resolved_from_backend_directory(monkeypatch):
    from backend.app import storage_paths

    monkeypatch.setenv("APP_DATA_DIR", "runtime-data")
    data_dir = storage_paths.get_data_dir()

    assert data_dir == Path(storage_paths.__file__).resolve().parents[1] / "runtime-data"
