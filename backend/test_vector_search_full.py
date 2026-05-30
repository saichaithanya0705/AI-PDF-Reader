"""
Manual full vector-search smoke probe.

Run with:
    python backend/test_vector_search_full.py

Requires SUPABASE_URL, SUPABASE_SERVICE_KEY, a running backend, and the sample PDF.
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


API_URL = os.getenv("API_URL", "http://localhost:8000")
TEST_PDF_PATH = Path(__file__).parent / "data/docs/edc6d62e-5b53-4e3a-88a2-aaecc35367ad_test.pdf"


async def run_full_vector_search_probe():
    import httpx
    from supabase import Client, create_client

    print("Starting Full Vector Search Verification...")
    load_dotenv()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    if not TEST_PDF_PATH.exists():
        raise SystemExit(f"Missing sample PDF: {TEST_PDF_PATH}")

    supabase: Client = create_client(url, key)
    email = os.getenv("TEST_VECTOR_EMAIL", "test_vector@example.com")
    password = os.getenv("TEST_VECTOR_PASSWORD", "Password123!")

    try:
        users = supabase.auth.admin.list_users()
        user = next((u for u in users if u.email == email), None)

        if user:
            print(f"Found existing test user: {user.id}")
        else:
            print("Creating new test user...")
            created_user = supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
            })
            print(f"Created test user: {created_user.user.id}")

        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        access_token = auth_response.session.access_token
        print("Logged in successfully")
    except Exception as exc:
        raise SystemExit(f"Auth failed: {exc}") from exc

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{API_URL}/")
            print("Backend is reachable")
        except Exception as exc:
            raise SystemExit(f"Backend not reachable at {API_URL}: {exc}") from exc

        print("\nUploading Document A...")
        with TEST_PDF_PATH.open("rb") as pdf_a:
            response = await client.post(
                f"{API_URL}/api/upload",
                headers=headers,
                files={"file": ("doc_a.pdf", pdf_a, "application/pdf")},
            )
        if response.status_code != 200:
            raise SystemExit(f"Upload A failed: {response.text}")
        doc_a_id = response.json()["document_id"]
        print(f"Doc A uploaded: {doc_a_id}")

        print("\nUploading Document B...")
        with TEST_PDF_PATH.open("rb") as pdf_b:
            response = await client.post(
                f"{API_URL}/api/upload",
                headers=headers,
                files={"file": ("doc_b.pdf", pdf_b, "application/pdf")},
            )
        if response.status_code != 200:
            raise SystemExit(f"Upload B failed: {response.text}")
        doc_b_id = response.json()["document_id"]
        print(f"Doc B uploaded: {doc_b_id}")

        print("Waiting 10s for embedding generation...")
        await asyncio.sleep(10)

        print("\nTesting Chat (View: Doc A, Query: 'summary')...")
        chat_payload = {
            "message": "What is this document about?",
            "history": [],
            "context_type": "pdf_viewer",
            "document_id": doc_a_id,
            "current_page": 1,
        }

        response = await client.post(f"{API_URL}/api/chat", headers=headers, json=chat_payload)
        if response.status_code != 200:
            raise SystemExit(f"Chat failed: {response.text}")

        data = response.json()
        related_docs = data.get("context", {}).get("related_documents", [])

        print(f"\nFound {len(related_docs)} related documents:")
        found_doc_b = False
        for doc in related_docs:
            print(
                f"   - {doc['document_name']} "
                f"(Page {doc['page_number']}) - Sim: {doc['similarity']:.4f}"
            )
            if doc["document_id"] == doc_b_id:
                found_doc_b = True

        if found_doc_b:
            print("\nSUCCESS: Doc B was found while viewing Doc A.")
        else:
            raise SystemExit("FAILURE: Doc B was not found in related documents.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    asyncio.run(run_full_vector_search_probe())
