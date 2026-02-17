
import os


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


vite_supabase_anon_key = require_env("VITE_SUPABASE_ANON_KEY")
supabase_service_key = require_env("SUPABASE_SERVICE_KEY")
supabase_url = require_env("SUPABASE_URL")
supabase_jwt_secret = require_env("SUPABASE_JWT_SECRET")
google_api_key = require_env("GOOGLE_API_KEY")
anthropic_api_key = require_env("ANTHROPIC_API_KEY")
azure_tts_key = require_env("AZURE_TTS_KEY")

backend_env = f"""LLM_PROVIDER=gemini
GOOGLE_API_KEY={google_api_key}
ANTHROPIC_API_KEY={anthropic_api_key}
ANTHROPIC_MODEL=claude-3-haiku-20240307
SUPABASE_URL={supabase_url}
SUPABASE_SERVICE_KEY={supabase_service_key}
SUPABASE_JWT_SECRET='{supabase_jwt_secret}'
GEMINI_MODEL=gemini-2.5-flash
FRONTEND_URL=https://64-227-179-63.sslip.io
AZURE_TTS_KEY={azure_tts_key}
AZURE_TTS_ENDPOINT=https://eastasia.api.cognitive.microsoft.com/
AZURE_TTS_DEPLOYMENT=tts
AZURE_TTS_VOICE=alloy
AZURE_TTS_API_VERSION=2025-03-01-preview
TTS_PROVIDER=azure
USE_SUPABASE=true
"""

frontend_env = f"""VITE_API_URL=https://64-227-179-63.sslip.io
VITE_SUPABASE_URL={supabase_url}
VITE_SUPABASE_ANON_KEY={vite_supabase_anon_key}
"""

print("Writing backend .env...")
with open("/var/www/pdfapp/backend/.env", "w") as f:
    f.write(backend_env)

print("Writing frontend .env...")
with open("/var/www/pdfapp/frontend/.env", "w") as f:
    f.write(frontend_env)

print("Updated remote .env files successfully")
