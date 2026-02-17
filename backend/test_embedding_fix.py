"""
Test script to verify embedding generation is working correctly
"""
import sys
sys.path.append('.')

from backend.app.embedding_service import get_embedding_service

print("=" * 60)
print("Testing Embedding Service")
print("=" * 60)

# Initialize service
service = get_embedding_service()

print("\n📝 Testing single embedding generation...")
test_text = "This is a test sentence about machine learning and artificial intelligence."
embedding = service.generate_embedding(test_text)

print(f"\n✅ Generated embedding:")
print(f"   - Length: {len(embedding)}")
print(f"   - First 10 values: {embedding[:10]}")
print(f"   - Norm: {sum(x**2 for x in embedding)**0.5:.4f}")
print(f"   - Is zero vector: {all(x == 0.0 for x in embedding)}")

if all(x == 0.0 for x in embedding):
    print("\n❌ WARNING: Embedding is a zero vector!")
    print("   This means the model is not generating actual embeddings.")
else:
    print("\n✅ SUCCESS: Real embeddings are being generated!")

print("\n📝 Testing batch embedding generation...")
test_texts = [
    "Machine learning is fascinating.",
    "Natural language processing enables computers to understand text.",
    "Vector embeddings capture semantic meaning."
]

embeddings = service.generate_embeddings_batch(test_texts, show_progress=False)

print(f"\n✅ Generated {len(embeddings)} embeddings:")
for i, emb in enumerate(embeddings):
    is_zero = all(x == 0.0 for x in emb)
    print(f"   - Text {i+1}: length={len(emb)}, is_zero={is_zero}")

print("\n📝 Testing similarity computation...")
if len(embeddings) >= 2:
    similarity = service.compute_similarity(embeddings[0], embeddings[1])
    print(f"\n✅ Similarity between text 1 and 2: {similarity:.4f}")
    
    if similarity > 0:
        print("   ✅ Similarity is non-zero, embeddings are meaningful!")
    else:
        print("   ❌ Similarity is zero, might be dummy embeddings.")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
