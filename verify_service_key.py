
import jwt
import os

key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxZXFjdHplYW5sb215bnd3d2NnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mjg2NjA1MywiZXhwIjoyMDc4NDQyMDUzfQ.PCYkL7I5Tc8pF4l8ulI6YuNHNclr__XnZjci-mQu7eY"
secret = "rayDYIGN286sCrUjnw0xa1u/kr/wLIjxt3CgC51STIFUkgUbD07p0NDeG7qN3d6rThGEXY91bXosU4TzgKGBYA=="

try:
    decoded = jwt.decode(key, secret, algorithms=["HS256"], options={"verify_aud": False})
    print("✅ Service Key Verified!")
    print(decoded)
except Exception as e:
    print(f"❌ Verification Failed: {e}")
