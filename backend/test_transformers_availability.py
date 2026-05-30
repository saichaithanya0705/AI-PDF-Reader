"""
Manual transformers availability diagnostic.

Run with:
    python backend/test_transformers_availability.py
"""


def main():
    print("=" * 60)
    print("Checking Library Availability")
    print("=" * 60)

    print("\n1. Testing transformers import...")
    try:
        import transformers

        print(f"   transformers version: {transformers.__version__}")
    except Exception as exc:
        print(f"   Failed: {exc}")

    print("\n2. Testing AutoTokenizer and AutoModel...")
    try:
        from transformers import AutoModel, AutoTokenizer  # noqa: F401

        print("   AutoTokenizer and AutoModel imported successfully")
    except Exception as exc:
        print(f"   Failed: {exc}")

    print("\n3. Testing model loading from HuggingFace...")
    try:
        from transformers import AutoModel, AutoTokenizer

        model_path = "sentence-transformers/all-MiniLM-L6-v2"
        print(f"   Loading tokenizer from: {model_path}")
        AutoTokenizer.from_pretrained(model_path)
        print("   Tokenizer loaded")

        print(f"   Loading model from: {model_path}")
        model = AutoModel.from_pretrained(model_path)
        print("   Model loaded")
        print(f"   Model type: {type(model)}")
    except Exception as exc:
        print(f"   Failed: {exc}")
        import traceback

        traceback.print_exc()

    print("\n4. Testing sentence_transformers...")
    try:
        from sentence_transformers import SentenceTransformer

        print("   SentenceTransformer imported")
        SentenceTransformer("all-MiniLM-L6-v2")
        print("   Model loaded via sentence_transformers")
    except Exception as exc:
        print(f"   Failed: {exc}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Diagnostic complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
