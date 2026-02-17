import os
from dotenv import load_dotenv
import requests
from pathlib import Path

# Load env
root_env = Path(__file__).parent.parent / '.env'
load_dotenv(root_env)

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")

if not SUPABASE_URL:
    print("❌ SUPABASE_URL not found")
    exit(1)

SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

jwks_paths = [
    "/auth/v1/jwks",
    "/auth/v1/.well-known/jwks.json",
    "/.well-known/jwks.json",
    "/auth/v1/jwks.json"
]

headers = {"apikey": SUPABASE_KEY}

for path in jwks_paths:
    url = f"{SUPABASE_URL}{path}"
    print(f"Checking: {url}")
    try:
        r = requests.get(url, headers=headers)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("✅ JWKS found!")
            print(r.text)
            break
    except Exception as e:
        print(f"Exception: {e}")
