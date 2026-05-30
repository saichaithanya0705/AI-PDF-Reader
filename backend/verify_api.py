"""
Integration checks against a running backend. Credentials from environment only.

  TEST_EMAIL, TEST_PASSWORD — Supabase test user
  BASE_URL — default http://127.0.0.1:8080
"""
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

root_env = Path(__file__).parent.parent / ".env"
load_dotenv(root_env)

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8080")
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")


def get_auth_token():
    print("[AUTH] Authenticating...")
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Supabase credentials not found in env.", file=sys.stderr)
        return None
    if not TEST_EMAIL or not TEST_PASSWORD:
        print("Set TEST_EMAIL and TEST_PASSWORD in .env for authenticated tests.", file=sys.stderr)
        return None

    try:
        from supabase import create_client

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = supabase.auth.sign_in_with_password(
            {"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        print(f"Authenticated as {res.user.email}")
        return res.session.access_token
    except Exception as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        return None


def test_memory(auth_token=None):
    print("\n[TEST 1] Chatbot Memory")
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    history = []
    msg1 = "Hello, my secret code is 9988."
    payload1 = {"message": msg1, "context_type": "library", "conversation_history": history}
    print(f"User: {msg1}")
    try:
        r1 = requests.post(f"{BASE_URL}/api/chat", json=payload1, headers=headers, timeout=120)
        if r1.status_code != 200:
            print(f"Msg 1 failed: {r1.status_code} - {r1.text}")
            return False
        resp1 = r1.json().get("response", "")
        print(f"Assistant: {resp1}")
        session_id = r1.json().get("session_id")
        history.append({"role": "user", "content": msg1})
        history.append({"role": "assistant", "content": resp1})
        msg2 = "What is the secret code I just told you?"
        payload2 = {
            "message": msg2,
            "context_type": "library",
            "conversation_history": history,
            "session_id": session_id,
        }
        print(f"User: {msg2}")
        r2 = requests.post(f"{BASE_URL}/api/chat", json=payload2, headers=headers, timeout=120)
        resp2 = r2.json().get("response", "")
        print(f"Assistant: {resp2}")
        if "9988" in resp2:
            print("TEST PASSED: Memory working.")
            return True
        print("TEST FAILED: Memory not working.")
        return False
    except Exception as e:
        print(f"Exception: {e}")
        return False


def test_library_context(auth_token=None):
    print("\n[TEST 2] Library Context (Hybrid RAG)")
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    msg = "Summarize the documents in the library."
    payload = {"message": msg, "context_type": "library", "conversation_history": []}
    print(f"User: {msg}")
    try:
        r = requests.post(f"{BASE_URL}/api/chat", json=payload, headers=headers, timeout=120)
        if r.status_code != 200:
            print(f"Request failed: {r.status_code} - {r.text}")
            return False
        resp = r.json().get("response", "")
        print(f"Assistant: {resp}")
        if len(resp) > 10:
            print("TEST PASSED: Received response from library context.")
            return True
        print("TEST FAILED: Response too short or empty.")
        return False
    except Exception as e:
        print(f"Exception: {e}")
        return False


def check_health():
    print("[INIT] Checking Backend Health...")
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if r.status_code == 200:
            print("Backend is UP.")
            return True
        print(f"Backend returned {r.status_code}: {r.text}")
    except Exception as e:
        print(f"Exception connecting to backend: {e}")
    print("Backend is DOWN.")
    return False


if __name__ == "__main__":
    if not check_health():
        sys.exit(1)
    token = get_auth_token()
    m = test_memory(token)
    l = test_library_context(token)
    if m and l:
        print("\nALL TESTS PASSED")
        sys.exit(0)
    print("\nSOME TESTS FAILED")
    sys.exit(1)
