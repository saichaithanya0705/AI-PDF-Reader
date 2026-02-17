import asyncio
import os
import sys
from pathlib import Path
import httpx
import json

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Configuration
API_URL = "http://localhost:8000"
TEST_PDF_PATH = Path(__file__).parent / "data/docs/edc6d62e-5b53-4e3a-88a2-aaecc35367ad_test.pdf"

async def test_full_vector_search():
    print("🧪 Starting Full Vector Search Verification...")
    
    # 1. Authenticate / Get User
    # For local testing with optional auth, we can just use a hardcoded user_id if we want,
    # but let's try to be proper and use the same logic as test_upload.py if possible.
    # Or simpler: just use the admin secret to get a user or create one.
    # Actually, since we enabled optional auth, we can just pass a user_id header if we want to simulate a specific user,
    # OR we can rely on the backend's behavior.
    # However, the vector search FILTERS by user_id. So we MUST have a consistent user_id.
    # The backend `get_optional_user` tries to get user from Supabase.
    # If we don't provide a token, it returns None.
    # If user is None, `build_pdf_context` might fail or use a default?
    # Let's check `build_pdf_context`: it takes `user_id`.
    # In `api/chat`, if user is None, it passes None to `build_pdf_context`.
    # `build_pdf_context` passes `user_id` to `search_related_documents`.
    # `search_related_documents` uses `user_id` to filter.
    # If `user_id` is None, the query `filter_user_id` will be None.
    # The RPC `match_documents` likely expects a UUID.
    
    # So we NEED a valid user_id.
    # We will use the SUPABASE_SERVICE_KEY to get a user ID from the auth admin API, similar to test_upload.py.
    
    from supabase import create_client, Client
    url: str = os.environ.get("SUPABASE_URL")
import asyncio
import os
import sys
from pathlib import Path
import httpx
import json

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Configuration
API_URL = "http://localhost:8000"
TEST_PDF_PATH = Path(__file__).parent / "data/docs/edc6d62e-5b53-4e3a-88a2-aaecc35367ad_test.pdf"

async def test_full_vector_search():
    print("Starting Full Vector Search Verification...")
    
    # 1. Authenticate / Get User
    # For local testing with optional auth, we can just use a hardcoded user_id if we want,
    # but let's try to be proper and use the same logic as test_upload.py if possible.
    # Or simpler: just use the admin secret to get a user or create one.
    # Actually, since we enabled optional auth, we can just pass a user_id header if we want to simulate a specific user,
    # OR we can rely on the backend's behavior.
    # However, the vector search FILTERS by user_id. So we MUST have a consistent user_id.
    # The backend `get_optional_user` tries to get user from Supabase.
    # If we don't provide a token, it returns None.
    # If user is None, `build_pdf_context` might fail or use a default?
    # Let's check `build_pdf_context`: it takes `user_id`.
    # In `api/chat`, if user is None, it passes None to `build_pdf_context`.
    # `build_pdf_context` passes `user_id` to `search_related_documents`.
    # `search_related_documents` uses `user_id` to filter.
    # If `user_id` is None, the query `filter_user_id` will be None.
    # The RPC `match_documents` likely expects a UUID.
    
    # So we NEED a valid user_id.
    # We will use the SUPABASE_SERVICE_KEY to get a user ID from the auth admin API, similar to test_upload.py.
    
    from supabase import create_client, Client
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(url, key)
    
    # Get the first user
    users = supabase.auth.admin.list_users()
    if not users:
        print("No users found in Supabase. Please create a user first.")
        return
    
    user_id = users[0].id
    user_email = users[0].email
    print(f"Using User ID: {user_id} ({user_email})")
    
    # We need a valid JWT for this user to pass to the API, OR we can mock it if we are running locally?
    # The `get_optional_user` verifies the JWT.
    # Generating a valid JWT locally without the user's password is hard.
    # BUT, we modified `auth_middleware.py` to be optional.
    # Wait, if we don't pass a token, `user` is None.
    # We need `user` to be populated.
    # We can't easily spoof the token verification unless we disable it or use a test token.
    
    # ALTERNATIVE: We can modify `search_related_documents` to handle None user_id (e.g. search all public docs?),
    # but that's not the requirement.
    
    # EASIER PATH: Login with a known test user credentials if we have them.
    # If not, we might have to skip the API layer and test the service directly,
    # BUT we want to test the API integration.
    
    # Let's try to login with the credentials from `test_upload.py` if they exist.
    # `test_upload.py` uses `test@example.com` / `password`.
    
    # Try to get or create user via Admin API to avoid email verification issues
    email = "test_vector@example.com"
    password = "Password123!"
    
    try:
        # Check if user exists
        users = supabase.auth.admin.list_users()
        user = next((u for u in users if u.email == email), None)
        
        if user:
            print(f"Found existing test user: {user.id}")
            user_id = user.id
        else:
            print("Creating new test user...")
            user = supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True
            })
            user_id = user.user.id
            print(f"Created test user: {user_id}")
            
        # Sign in to get access token
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        access_token = auth_response.session.access_token
        print("Logged in successfully")
        
    except Exception as e:
        print(f"Auth failed: {e}")
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        # Check if backend is running
        try:
            await client.get(f"{API_URL}/")
            print("Backend is reachable")
        except Exception as e:
            print(f"Backend not reachable at {API_URL}. Is it running? Error: {e}")
            return
        # 2. Upload Doc A
        print("\nUploading Document A...")
        files = {'file': ('doc_a.pdf', open(TEST_PDF_PATH, 'rb'), 'application/pdf')}
        response = await client.post(f"{API_URL}/api/upload", headers=headers, files=files)
        if response.status_code != 200:
            print(f"Upload A failed: {response.text}")
            return
        doc_a_id = response.json()['document_id']
        print(f"Doc A uploaded: {doc_a_id}")

        # 3. Upload Doc B
        print("\nUploading Document B...")
        # We use the same file content but different name
        files = {'file': ('doc_b.pdf', open(TEST_PDF_PATH, 'rb'), 'application/pdf')}
        response = await client.post(f"{API_URL}/api/upload", headers=headers, files=files)
        if response.status_code != 200:
            print(f"Upload B failed: {response.text}")
            return
        doc_b_id = response.json()['document_id']
        print(f"Doc B uploaded: {doc_b_id}")

        # Wait a bit for processing (embeddings generation)
        print("Waiting 10s for embedding generation...")
        await asyncio.sleep(10)

        # 4. Chat in PDF Context (Viewing Doc A)
        print("\nTesting Chat (View: Doc A, Query: 'summary')...")
        # We ask for a summary. Since Doc B is identical, it should be very relevant.
        chat_payload = {
            "message": "What is this document about?",
            "history": [],
            "context_type": "pdf_viewer",
            "document_id": doc_a_id,
            "current_page": 1
        }
        
        response = await client.post(f"{API_URL}/api/chat", headers=headers, json=chat_payload)
        
        if response.status_code != 200:
            print(f"Chat failed: {response.text}")
            return
            
        data = response.json()
        print("Chat response received")
        
        # 5. Verify Related Documents
        context = data.get("context", {})
        related_docs = context.get("related_documents", [])
        
        print(f"\nFound {len(related_docs)} related documents:")
        found_doc_b = False
        for doc in related_docs:
            print(f"   - {doc['document_name']} (Page {doc['page_number']}) - Sim: {doc['similarity']:.4f}")
            if doc['document_id'] == doc_b_id:
                found_doc_b = True
        
        if found_doc_b:
            print("\nSUCCESS: Doc B was found while viewing Doc A!")
        else:
            print("\nFAILURE: Doc B was NOT found in related documents.")
            # It might be that embeddings weren't ready or threshold was too high?
            # Or maybe because they are identical, it was filtered out? 
            # (No, only current_doc_id is filtered)

if __name__ == "__main__":
    asyncio.run(test_full_vector_search())
