"""
Diagnostic script to check transformers availability
"""

print("=" * 60)
print("Checking Library Availability")
print("=" * 60)

# Test 1: Can we import transformers?
print("\n1. Testing transformers import...")
try:
    import transformers
    print(f"   ✅ transformers version: {transformers.__version__}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 2: Can we import AutoTokenizer and AutoModel?
print("\n2. Testing AutoTokenizer and AutoModel...")
try:
    from transformers import AutoTokenizer, AutoModel
    print("   ✅ AutoTokenizer and AutoModel imported successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 3: Can we load a specific model?
print("\n3. Testing model loading from HuggingFace...")
try:
    from transformers import AutoTokenizer, AutoModel
    model_path = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"   Loading tokenizer from: {model_path}")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    print("   ✅ Tokenizer loaded")
    
    print(f"   Loading model from: {model_path}")
    model = AutoModel.from_pretrained(model_path)
    print("   ✅ Model loaded")
    print(f"   Model type: {type(model)}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Can we use sentence_transformers?
print("\n4. Testing sentence_transformers...")
try:
    from sentence_transformers import SentenceTransformer
    print("   ✅ SentenceTransformer imported")
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("   ✅ Model loaded via sentence_transformers")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Diagnostic complete!")
print("=" * 60)
