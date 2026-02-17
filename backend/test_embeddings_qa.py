import unittest
import sys
import os
import shutil
import numpy as np
from typing import List

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.embedding_service import EmbeddingService
from backend.app.vector_store import FAISSVectorStore

class TestEmbeddingSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[QA] Setting up test environment...")
        cls.test_dir = "test_data"
        os.makedirs(cls.test_dir, exist_ok=True)
        
        # Initialize services
        cls.embedding_service = EmbeddingService()
        cls.vector_store_path = os.path.join(cls.test_dir, "test_index.bin")
        cls.metadata_path = os.path.join(cls.test_dir, "test_metadata.pkl")
        cls.vector_store = FAISSVectorStore(
            index_path=cls.vector_store_path,
            metadata_path=cls.metadata_path
        )

    @classmethod
    def tearDownClass(cls):
        print("\n[QA] Cleaning up test environment...")
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def test_01_embedding_generation_sanity(self):
        """Test basic embedding generation dimensions and non-zero values"""
        print("\n[Test] Embedding Generation Sanity")
        text = "This is a test sentence."
        embedding = self.embedding_service.generate_embedding(text)
        
        self.assertEqual(len(embedding), 384, "Embedding dimension should be 384")
        self.assertFalse(all(v == 0 for v in embedding), "Embedding should not be a zero vector")
        self.assertTrue(any(v != 0 for v in embedding), "Embedding should contain non-zero values")
        print("[Pass] Embedding dimensions and content verified")

    def test_02_embedding_consistency(self):
        """Test that same input produces same embedding"""
        print("\n[Test] Embedding Consistency")
        text = "Consistency check."
        emb1 = self.embedding_service.generate_embedding(text)
        emb2 = self.embedding_service.generate_embedding(text)
        
        np.testing.assert_array_almost_equal(emb1, emb2, decimal=6, err_msg="Embeddings for same text should be identical")
        print("[Pass] Deterministic embedding generation verified")

    def test_03_batch_processing(self):
        """Test batch generation efficiency and correctness"""
        print("\n[Test] Batch Processing")
        texts = ["Sentence 1", "Sentence 2", "Sentence 3"]
        embeddings = self.embedding_service.generate_embeddings_batch(texts)
        
        self.assertEqual(len(embeddings), 3, "Should return 3 embeddings")
        for emb in embeddings:
            self.assertEqual(len(emb), 384)
            self.assertFalse(all(v == 0 for v in emb))
        print("[Pass] Batch processing verified")

    def test_04_edge_cases_empty_input(self):
        """Test handling of empty and whitespace inputs"""
        print("\n[Test] Edge Cases: Empty Input")
        
        # Empty string
        emb_empty = self.embedding_service.generate_embedding("")
        self.assertTrue(all(v == 0 for v in emb_empty), "Empty input should return zero vector")
        
        # Whitespace
        emb_space = self.embedding_service.generate_embedding("   ")
        self.assertTrue(all(v == 0 for v in emb_space), "Whitespace input should return zero vector")
        
        # None (if type checking allows, or handled) - Python type hint says str, but good to check robustness if possible
        # skipping None to avoid type errors if strict, but let's test batch with empty
        
        batch_mixed = ["Valid", "", "   "]
        embeddings = self.embedding_service.generate_embeddings_batch(batch_mixed)
        self.assertFalse(all(v == 0 for v in embeddings[0]), "Valid text should have non-zero embedding")
        self.assertTrue(all(v == 0 for v in embeddings[1]), "Empty text in batch should have zero embedding")
        self.assertTrue(all(v == 0 for v in embeddings[2]), "Whitespace text in batch should have zero embedding")
        print("[Pass] Empty/Whitespace input handling verified")

    def test_05_edge_cases_long_input(self):
        """Test handling of inputs exceeding model context length"""
        print("\n[Test] Edge Cases: Long Input")
        # Generate long text > 512 tokens approx
        long_text = "word " * 1000 
        try:
            embedding = self.embedding_service.generate_embedding(long_text)
            self.assertEqual(len(embedding), 384)
            self.assertFalse(all(v == 0 for v in embedding))
            print("[Pass] Long input truncation/handling verified")
        except Exception as e:
            self.fail(f"Long input caused exception: {e}")

    def test_06_vector_store_add_and_search(self):
        """Test adding documents to FAISS and searching"""
        print("\n[Test] FAISS Add and Search")
        
        docs = [
            "The quick brown fox jumps over the lazy dog.",
            "Machine learning is fascinating.",
            "Python is a popular programming language.",
            "Adobe Hackathon is fun."
        ]
        metadatas = [
            {"id": 1, "text": docs[0], "category": "animals"},
            {"id": 2, "text": docs[1], "category": "tech"},
            {"id": 3, "text": docs[2], "category": "tech"},
            {"id": 4, "text": docs[3], "category": "event"}
        ]
        
        embeddings = self.embedding_service.generate_embeddings_batch(docs)
        self.vector_store.add_documents(embeddings, metadatas)
        
        # Search for "coding"
        query = "coding language"
        query_emb = self.embedding_service.generate_embedding(query)
        results = self.vector_store.search(query_emb, k=2)
        
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['id'], 3, "Should find Python doc as most relevant to coding")
        print(f"[Pass] Search accuracy check: Found '{results[0]['text']}' for query '{query}'")

    def test_07_vector_store_filtering(self):
        """Test metadata filtering in search"""
        print("\n[Test] FAISS Metadata Filtering")
        
        query = "technology"
        query_emb = self.embedding_service.generate_embedding(query)
        
        # Filter for category='animals' (should match the fox sentence even if relevance is low, or nothing if threshold)
        # Actually our search implementation does hard filtering
        
        filter_criteria = {"category": "animals"}
        results = self.vector_store.search(query_emb, k=1, filter_criteria=filter_criteria)
        
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['category'], "animals")
        self.assertEqual(results[0]['id'], 1)
        print("[Pass] Metadata filtering verified")

    def test_08_persistence(self):
        """Test saving and loading the index"""
        print("\n[Test] Persistence (Save/Load)")
        
        # Create new instance pointing to same paths
        new_store = FAISSVectorStore(
            index_path=self.vector_store_path,
            metadata_path=self.metadata_path
        )
        
        self.assertEqual(new_store.index.ntotal, 4, "Should load 4 vectors from disk")
        self.assertEqual(len(new_store.metadata), 4, "Should load 4 metadata entries")
        
        # Verify search still works
        query = "fox"
        query_emb = self.embedding_service.generate_embedding(query)
        results = new_store.search(query_emb, k=1)
        self.assertEqual(results[0]['id'], 1)
        print("[Pass] Persistence verified")

if __name__ == '__main__':
    unittest.main()
