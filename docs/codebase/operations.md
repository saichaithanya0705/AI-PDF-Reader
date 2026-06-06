# Operations And Developer Workflow

## Repository Layout

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI app, support scripts, requirements, migrations, and tests |
| `frontend/` | Vite/React app, public assets, tests, and build config |
| `docs/codebase/` | codebase documentation added for maintainers |
| `.github/workflows/` | CI and deployment workflows |
| `graphify-out/` | generated architecture graph outputs and report |
| `supabase/` | local Supabase CLI metadata directory, currently only temp artifacts |

## Local Development Workflow

### Backend

1. Copy root `.env.example` to `.env`.
2. Install Python dependencies from `backend/requirements-minimal.txt` or `backend/requirements.txt`.
3. Run `python run_app.py`.
4. The backend listens on `http://localhost:8080` unless `PORT` overrides it.

### Frontend

1. Copy `frontend/.env.example` or `frontend/.env.local.example` into the chosen local env file.
2. Run `npm ci` inside `frontend/`.
3. Run `npm run dev`.
4. The frontend listens on `http://localhost:5173`.

## Environment Variables

### Backend-side env

The code actively uses or documents these families of settings:

- LLM provider selection: `LLM_PROVIDER`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, Azure settings, Ollama settings
- auth and tenancy: `USE_SUPABASE`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`
- dev bypass: `APP_ENV`, `AUTH_BYPASS_ENABLED`, `DEV_AUTH_EMAIL`, `DEV_AUTH_USER_ID`
- upload/runtime safety: `ALLOW_CLIENT_ID_FALLBACK`, `CORS_ORIGINS`, `MAX_PDF_UPLOAD_BYTES`, `MAX_PDF_TRANSFORM_BYTES`
- TTS: `TTS_PROVIDER`, Azure TTS settings, Google TTS settings

### Frontend-side env

- `VITE_APP_ENV`
- `VITE_API_URL`
- `VITE_WS_URL` when explicitly provided
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_AUTH_BYPASS_ENABLED`
- `VITE_DEV_AUTH_EMAIL`
- `VITE_DEV_AUTH_USER_ID`

## CI And Deployment

### CI / canonical workflow

`.github/workflows/deploy.yml` is the main automation path. It:

- installs frontend dependencies with `npm ci`
- runs frontend tests, lint, typecheck, and build
- installs backend dependencies from `backend/requirements.txt`
- runs `python -m pytest backend/tests -q`
- deploys only after verification succeeds

`.github/workflows/main_ai-pdf-reader.yml` is intentionally obsolete and manual-only.

### Server scripts

| File | Role |
| --- | --- |
| `deploy_backend.sh` | production backend install and preparation script |
| `deploy_frontend.sh` | production frontend build script |
| `setup_droplet.sh` | DigitalOcean host bootstrap |
| `setup_services.sh` | service and nginx setup |
| `pdfapp-backend.service` | systemd unit file |
| `nginx.conf` | main nginx reverse-proxy config |
| `nginx_ssl.conf` | SSL-oriented nginx config |
| `upload_to_droplet.bat` | Windows upload helper |
| `update_remote_env.py` | remote environment update helper |

### Deployment reference docs

| File | Role |
| --- | --- |
| `README.md` | quick-start setup |
| `DEPLOY_DIGITALOCEAN.md` | detailed droplet deployment notes |
| `PORT_CONFIGURATION.md` | local and production port map |

## Support Scripts And Diagnostics

### Root-level support

- `check_models.py`: model/dependency inspection helper
- `debug_import_path.py`: Python import-path troubleshooting
- `debug_sqlite.py`: SQLite inspection helper
- `make_dummy_pdf.py`: sample PDF generator
- `verify_env.py`: environment validation helper
- `verify_jwt.py`, `verify_service_key.py`: auth secret verification helpers
- `test_advanced_rag.py`: ad-hoc RAG test script

### Backend support

- `backend/check_genai_env.py`, `backend/check_imports.py`, `backend/check_jwks.py`
- `backend/clean_orphaned_entries.py`, `backend/fix_database_paths.py`
- `backend/process_documents_for_rag.py`
- `backend/read_log.py`, `backend/read_run_log.py`
- `backend/verify_api.py`, `backend/verify_chat.py`, `backend/verify_gemini.py`, `backend/verify_manual.py`, `backend/verify_rag_local.py`
- legacy or manual test scripts such as `backend/test_upload.py` and `backend/test_vector_search_full.py`

## Architecture Tooling

### Graphify

`_graphify_build.py` generates:

- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/graph.json`
- `graphify-out/graph.html`

The current graph report highlights `IntelligentPDFBrain`, `HighPerformancePDFProcessor`, `DocumentDatabase`, `SupabaseDatabase`, `SectionHighlighter`, `apiRequest()`, `PDFValidator`, `EnhancedLLMService`, `RAGService`, and `SmartUploadHandler` as the most connected abstractions. Some of those names reflect older code or graph snapshots, so use the report as a navigation aid and verify against live files.

## Generated And Local-State Directories

These exist in the repo or on developer machines but are not maintained source:

- `frontend/node_modules/`
- frontend `dist/`
- Python `__pycache__` folders
- `backend/data/` runtime databases and uploaded docs
- `.log`, `.db`, `.sqlite*`, `.pkl`, `.pyc` artifacts
- `graphify-out/cache/`
- `supabase/.temp/`

## Known Drift To Watch

| Drift | Why it matters |
| --- | --- |
| `frontend/src/config.ts` defaulting to port `8000` while docs use `8080` | local setup can silently point at the wrong backend |
| frontend env filename mismatch between README, examples, and deploy script | onboarding friction and config mistakes |
| `backend/.env.example` using `FRONTEND_URL` while runtime reads `CORS_ORIGINS` | CORS configuration can be misunderstood |
| deploy docs/scripts naming different service or deploy roots in places | deployment maintenance requires cross-checking before changes |
| multiple legacy or parallel implementations left in tree | refactors should verify what is actually wired into runtime |

## Practical Maintenance Rules

- Use `backend/requirements.txt` and `frontend/package-lock.json` as lockfile sources.
- Treat `.github/workflows/deploy.yml` as the CI source of truth before changing setup docs.
- Verify environment-variable names against runtime code, not just example files.
- When removing legacy scripts or modules, check both the manual verification scripts and the repo hygiene tests first.
