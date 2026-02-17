import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ No OPENAI_API_KEY found")
    exit(1)

client = OpenAI(api_key=api_key)

try:
    print("🧪 Testing OpenAI Embeddings...")
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input="Hello world"
    )
    embedding = response.data[0].embedding
    print(f"✅ Generated embedding: length {len(embedding)}")
    print(f"   First 5 values: {embedding[:5]}")
except Exception as e:
    print(f"❌ Failed to generate embedding: {e}")
