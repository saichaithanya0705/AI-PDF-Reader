"""
Verify a Supabase service-role JWT against SUPABASE_JWT_SECRET (env only).

Usage:
  set SUPABASE_JWT_SECRET=...
  set TEST_SERVICE_JWT=eyJ...
  python verify_service_key.py
"""
import os
import sys

from jose import jwt, JWTError

secret = os.getenv("SUPABASE_JWT_SECRET")
token = os.getenv("TEST_SERVICE_JWT")

if not secret:
    print("Set SUPABASE_JWT_SECRET in the environment.", file=sys.stderr)
    sys.exit(1)
if not token:
    print("Set TEST_SERVICE_JWT to a service-role JWT to verify.", file=sys.stderr)
    sys.exit(1)

try:
    decoded = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
    print("Service key verified.")
    print(decoded)
except JWTError as e:
    print(f"Verification failed: {e}", file=sys.stderr)
    sys.exit(1)
