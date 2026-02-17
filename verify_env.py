import sys
import os

print(f"Python Executable: {sys.executable}")

try:
    import faiss
    print("[OK] faiss imported successfully")
    index = faiss.IndexHNSWFlat(384, 32)
    print(f"[OK] FAISS HNSW index created: {index.ntotal} vectors")
except ImportError as e:
    print(f"[ERROR] faiss import failed: {e}")
except Exception as e:
    print(f"[ERROR] FAISS test failed: {e}")

try:
    from sentence_transformers import SentenceTransformer
    print("[OK] sentence_transformers imported successfully")
    # Don't load model to save time, just check import
except ImportError as e:
    print(f"[ERROR] sentence_transformers import failed: {e}")

try:
    import fastapi
    import uvicorn
    print("[OK] fastapi and uvicorn imported successfully")
except ImportError as e:
    print(f"[ERROR] web framework import failed: {e}")
