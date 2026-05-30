"""
Manual embedding and vector-store QA integration probe.

Run with:
    python backend/test_embeddings_qa.py

This loads the embedding model and writes a temporary FAISS index, so it stays
out of pytest's default unit-test collection.
"""

import shutil
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
TEST_DIR = BACKEND_DIR / "test_data"


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _assert_vectors_almost_equal(left, right, message):
    import numpy as np

    np.testing.assert_array_almost_equal(left, right, decimal=6, err_msg=message)


def _build_services():
    sys.path.insert(0, str(BACKEND_DIR.parent))

    from backend.app.embedding_service import EmbeddingService
    from backend.app.vector_store import FAISSVectorStore

    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir(parents=True)

    embedding_service = EmbeddingService()
    vector_store = FAISSVectorStore(
        index_path=str(TEST_DIR / "test_index.bin"),
        metadata_path=str(TEST_DIR / "test_metadata.pkl"),
    )
    return embedding_service, vector_store


def _check_embedding_generation_sanity(embedding_service):
    print("\n[QA] Embedding generation sanity")
    text = "This is a test sentence."
    embedding = embedding_service.generate_embedding(text)

    _assert(len(embedding) == 384, "Embedding dimension should be 384")
    _assert(not all(value == 0 for value in embedding), "Embedding should not be a zero vector")
    _assert(any(value != 0 for value in embedding), "Embedding should contain non-zero values")
    print("[Pass] Embedding dimensions and content verified")


def _check_embedding_consistency(embedding_service):
    print("\n[QA] Embedding consistency")
    text = "Consistency check."
    first = embedding_service.generate_embedding(text)
    second = embedding_service.generate_embedding(text)

    _assert_vectors_almost_equal(first, second, "Embeddings for same text should be identical")
    print("[Pass] Deterministic embedding generation verified")


def _check_batch_processing(embedding_service):
    print("\n[QA] Batch processing")
    texts = ["Sentence 1", "Sentence 2", "Sentence 3"]
    embeddings = embedding_service.generate_embeddings_batch(texts)

    _assert(len(embeddings) == 3, "Should return 3 embeddings")
    for embedding in embeddings:
        _assert(len(embedding) == 384, "Batch embedding dimension should be 384")
        _assert(not all(value == 0 for value in embedding), "Batch embedding should be non-zero")
    print("[Pass] Batch processing verified")


def _check_empty_and_whitespace_inputs(embedding_service):
    print("\n[QA] Empty and whitespace inputs")
    empty_embedding = embedding_service.generate_embedding("")
    whitespace_embedding = embedding_service.generate_embedding("   ")

    _assert(all(value == 0 for value in empty_embedding), "Empty input should return zero vector")
    _assert(
        all(value == 0 for value in whitespace_embedding),
        "Whitespace input should return zero vector",
    )

    embeddings = embedding_service.generate_embeddings_batch(["Valid", "", "   "])
    _assert(not all(value == 0 for value in embeddings[0]), "Valid text should be non-zero")
    _assert(all(value == 0 for value in embeddings[1]), "Empty batch item should be zero")
    _assert(all(value == 0 for value in embeddings[2]), "Whitespace batch item should be zero")
    print("[Pass] Empty and whitespace handling verified")


def _check_long_input(embedding_service):
    print("\n[QA] Long input")
    long_text = "word " * 1000
    embedding = embedding_service.generate_embedding(long_text)

    _assert(len(embedding) == 384, "Long input embedding dimension should be 384")
    _assert(not all(value == 0 for value in embedding), "Long input should produce non-zero embedding")
    print("[Pass] Long input truncation/handling verified")


def _check_vector_store_add_and_search(embedding_service, vector_store):
    print("\n[QA] FAISS add and search")
    documents = [
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is fascinating.",
        "Python is a popular programming language.",
        "Adobe Hackathon is fun.",
    ]
    metadatas = [
        {"id": 1, "text": documents[0], "category": "animals"},
        {"id": 2, "text": documents[1], "category": "tech"},
        {"id": 3, "text": documents[2], "category": "tech"},
        {"id": 4, "text": documents[3], "category": "event"},
    ]

    embeddings = embedding_service.generate_embeddings_batch(documents)
    vector_store.add_documents(embeddings, metadatas)

    query_embedding = embedding_service.generate_embedding("coding language")
    results = vector_store.search(query_embedding, k=2)

    _assert(results, "Search should return at least one result")
    _assert(results[0]["id"] == 3, "Should find Python doc as most relevant to coding")
    print(f"[Pass] Search found {results[0]['text']!r}")


def _check_vector_store_filtering(embedding_service, vector_store):
    print("\n[QA] FAISS metadata filtering")
    query_embedding = embedding_service.generate_embedding("technology")
    results = vector_store.search(
        query_embedding,
        k=1,
        filter_criteria={"category": "animals"},
    )

    _assert(results, "Filtered search should return at least one result")
    _assert(results[0]["category"] == "animals", "Filtered result should match category")
    _assert(results[0]["id"] == 1, "Filtered result should be the animal document")
    print("[Pass] Metadata filtering verified")


def _check_vector_store_persistence(embedding_service):
    print("\n[QA] FAISS persistence")
    from backend.app.vector_store import FAISSVectorStore

    persisted_store = FAISSVectorStore(
        index_path=str(TEST_DIR / "test_index.bin"),
        metadata_path=str(TEST_DIR / "test_metadata.pkl"),
    )

    _assert(persisted_store.index.ntotal == 4, "Should load 4 vectors from disk")
    _assert(len(persisted_store.metadata) == 4, "Should load 4 metadata entries")

    query_embedding = embedding_service.generate_embedding("fox")
    results = persisted_store.search(query_embedding, k=1)
    _assert(results[0]["id"] == 1, "Persisted search should find the animal document")
    print("[Pass] Persistence verified")


def main():
    print("[QA] Setting up embedding/vector-store probe")
    embedding_service, vector_store = _build_services()

    try:
        _check_embedding_generation_sanity(embedding_service)
        _check_embedding_consistency(embedding_service)
        _check_batch_processing(embedding_service)
        _check_empty_and_whitespace_inputs(embedding_service)
        _check_long_input(embedding_service)
        _check_vector_store_add_and_search(embedding_service, vector_store)
        _check_vector_store_filtering(embedding_service, vector_store)
        _check_vector_store_persistence(embedding_service)
    finally:
        if TEST_DIR.exists():
            shutil.rmtree(TEST_DIR)

    print("\n[QA] Embedding/vector-store probe complete")


if __name__ == "__main__":
    main()
