import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Import ONLY SupabaseDatabase, avoiding RAGService/SentenceTransformer dependencies
from app.supabase_database import get_supabase_db

async def verify_rag_direct():
    print("🧪 Starting Direct Supabase Verification...")
    
    # Ensure Supabase mode is on
    os.environ["USE_SUPABASE"] = "true"
    
    try:
        db = get_supabase_db()
        print("✅ Supabase Database initialized")
        
        # 1. Test Vector Search (using a mock embedding)
        print("\n1️⃣ Testing Vector Search (match_documents RPC)...")
        # Create a dummy embedding (384 dimensions for all-MiniLM-L6-v2)
        dummy_embedding = [0.1] * 384
        
        try:
            results = db.search_vectors(
                query_embedding=dummy_embedding,
                match_threshold=0.0, # Low threshold to match anything
                match_count=1,
                user_id="00000000-0000-0000-0000-000000000000" # Dummy UUID
            )
            print(f"✅ Vector search executed successfully. Found {len(results)} results.")
            print(f"   (Result count 0 is expected if DB is empty, but no error means RPC works)")
        except Exception as e:
            print(f"❌ Vector search failed: {e}")
            if hasattr(e, 'message'):
                print(f"Message: {e.message}")
            if hasattr(e, 'details'):
                print(f"Details: {e.details}")
            if hasattr(e, 'hint'):
                print(f"Hint: {e.hint}")
            return

        print("\n✨ Supabase Verification Complete!")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_rag_direct())
