"""
Manual OpenAI embedding smoke probe.

Run with:
    python backend/test_openai_embedding.py
"""
import os

from dotenv import load_dotenv


def main():
    from openai import OpenAI

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("No OPENAI_API_KEY found")

    client = OpenAI(api_key=api_key)

    try:
        print("Testing OpenAI Embeddings...")
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input="Hello world",
        )
        embedding = response.data[0].embedding
        print(f"Generated embedding: length {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")
    except Exception as exc:
        print(f"Failed to generate embedding: {exc}")


if __name__ == "__main__":
    main()
