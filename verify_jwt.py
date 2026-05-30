"""
Local JWT verification helper. Requires env vars only — never commit secrets.

Usage:
  set SUPABASE_JWT_SECRET=...
  set TEST_JWT=eyJ...
  python verify_jwt.py
"""
import os
import sys

from jose import jwt, JWTError

secret = os.getenv("SUPABASE_JWT_SECRET")
token = os.getenv("TEST_JWT")

if not secret:
    print("Set SUPABASE_JWT_SECRET in the environment.", file=sys.stderr)
    sys.exit(1)
if not token:
    print("Set TEST_JWT to a Supabase access token to verify.", file=sys.stderr)
    sys.exit(1)

try:
    decoded = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
    print("Signature verified.")
    print(decoded)
except JWTError as e:
    print(f"Verification failed: {e}", file=sys.stderr)
    sys.exit(1)
