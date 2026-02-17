
import jwt
import os

key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxZXFjdHplYW5sb215bnd3d2NnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4NjYwNTMsImV4cCI6MjA3ODQ0MjA1M30.UdIVDjhN9ufY1ihcU_Sel-ocXkXNV60yzp5Ujks-0v8"
secret = "rayDYIGN286sCrUjnw0xa1u/kr/wLIjxt3CgC51STIFUkgUbD07p0NDeG7qN3d6rThGEXY91bXosU4TzgKGBYA=="

try:
    decoded = jwt.decode(key, secret, algorithms=["HS256"], audience="authenticated") # audience might be empty or specific?
    # Supabase keys usually don't verify audience strictness by default in client, but let's try strict first, then loose
    print("✅ Signature Verified!")
    print(decoded)
except Exception as e:
    print(f"❌ Verification Failed: {e}")

    # Try without options
    try:
        decoded = jwt.decode(key, secret, algorithms=["HS256"], options={"verify_aud": False})
        print("✅ Signature Verified (No Aud Check)!")
        print(decoded)
    except Exception as e2:
        print(f"❌ Verification Failed Again: {e2}")

