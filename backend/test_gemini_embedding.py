"""
Manual Gemini embedding smoke probe.

Run with:
    python backend/test_gemini_embedding.py
"""
import os

from dotenv import load_dotenv


def main():
    import google.generativeai as genai

    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("No GOOGLE_API_KEY found")

    genai.configure(api_key=api_key)

    try:
        print("Testing Gemini Embeddings...")
        result = genai.embed_content(
            model="models/embedding-001",
            content="Hello world",
            task_type="retrieval_document",
        )
        embedding = result["embedding"]
        print(f"Generated embedding: length {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")
    except Exception as exc:
        print(f"Failed to generate embedding: {exc}")


if __name__ == "__main__":
    main()
