import sys

from backend.app.nvidia_api import NvidiaApiUnavailableError, require_nvidia_api_key
from backend.app.nvidia_retrieval_config import load_nvidia_embedding_config


def main() -> int:
    failures: list[str] = []
    print(f"Python Executable: {sys.executable}")

    try:
        import faiss

        embedding_config = load_nvidia_embedding_config()
        index = faiss.IndexHNSWFlat(embedding_config.dimension, 32)
        print(f"[OK] FAISS HNSW index created: {index.ntotal} vectors")
    except ImportError as exc:
        failures.append(f"faiss import failed: {exc}")
    except (RuntimeError, ValueError) as exc:
        failures.append(f"FAISS/configuration test failed: {exc}")

    try:
        require_nvidia_api_key()
        print("[OK] NVIDIA_API_KEY is configured for hosted embeddings")
    except NvidiaApiUnavailableError as exc:
        failures.append(f"hosted embedding configuration failed: {exc}")

    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401

        print("[OK] fastapi and uvicorn imported successfully")
    except ImportError as exc:
        failures.append(f"web framework import failed: {exc}")

    for failure in failures:
        print(f"[ERROR] {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    # Mirror backend/app/main.py, which loads the project-root .env at startup;
    # without this, a local run reports configured keys as missing.
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
    raise SystemExit(main())
