"""
Manual upload smoke probe.

Run with:
    python backend/test_upload.py

Requires Supabase service key and a running API on localhost:8080.
Optional env:
    TEST_EMAIL / TEST_PASSWORD
    BASE_URL (default http://localhost:8080)
"""
import os
import time
from pathlib import Path


def main():
    import requests
    from dotenv import load_dotenv
    from supabase import create_client

    load_dotenv(Path(__file__).parent.parent / ".env")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    base_url = os.getenv("BASE_URL", "http://localhost:8080")
    test_email = os.getenv("TEST_EMAIL")
    test_password = os.getenv("TEST_PASSWORD")

    if not supabase_url or not supabase_key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")

    supabase = create_client(supabase_url, supabase_key)

    token = None
    if test_email and test_password:
        session = supabase.auth.sign_in_with_password(
            {"email": test_email, "password": test_password}
        )
        token = session.session.access_token
    else:
        users_response = supabase.auth.admin.list_users()
        users = users_response if isinstance(users_response, list) else getattr(users_response, "users", [])
        if not users:
            raise SystemExit("No users in Supabase; set TEST_EMAIL and TEST_PASSWORD")
        user_id = users[0].id
        print(f"Using first admin user: {user_id}")

    pdf_content = b"%PDF-1.4\n%Test PDF Content"
    test_path = Path("test.pdf")
    test_path.write_bytes(pdf_content)

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{base_url}/upload/active_file"

    try:
        print(f"POST {url} (authenticated)")
        max_retries = 5
        for index in range(max_retries):
            try:
                with test_path.open("rb") as file_handle:
                    response = requests.post(
                        url,
                        files={"file": ("test.pdf", file_handle, "application/pdf")},
                        headers=headers,
                        timeout=60,
                    )
                print(f"Status: {response.status_code}")
                print(response.text)
                if response.status_code in (200, 202):
                    print("Upload successful.")
                    break
                break
            except requests.exceptions.ConnectionError:
                print(f"Connection failed, retry {index + 1}/{max_retries}")
                time.sleep(2)
        else:
            print("Could not connect to server.")
    finally:
        test_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
