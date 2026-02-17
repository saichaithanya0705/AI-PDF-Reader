import sentence_transformers
print(f"sentence_transformers version: {sentence_transformers.__version__}")
print(f"sentence_transformers file: {sentence_transformers.__file__}")

try:
    from sentence_transformers import CrossEncoder
    print("✅ CrossEncoder imported successfully")
except ImportError as e:
    print(f"❌ Failed to import CrossEncoder: {e}")

try:
    import sentence_transformers.cross_encoder
    print("✅ sentence_transformers.cross_encoder imported successfully")
except ImportError as e:
    print(f"❌ Failed to import sentence_transformers.cross_encoder: {e}")

print("Dir of sentence_transformers:")
print(dir(sentence_transformers))
