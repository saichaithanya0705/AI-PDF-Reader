# AI PDF Reader (Adobe Hackathon Finale)

React + FastAPI app for PDF upload, cross-document RAG chat, and insights. Auth and document storage use **Supabase**.

## Quick start

1. Copy `.env.example` to `.env` in the repo root and fill in Supabase + `GOOGLE_API_KEY` (or your chosen `LLM_PROVIDER`).
2. Copy `frontend/.env.example` to `frontend/.env.local` with `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and `VITE_API_URL=http://localhost:8080`.
3. Install dependencies:
   - `pip install -r backend/requirements-minimal.txt` (or `requirements.txt` for full stack)
   - `cd frontend && npm ci`
4. Run: `python run_app.py` → API on **http://localhost:8080**
5. In another terminal: `cd frontend && npm run dev` → UI on **http://localhost:5173**

## Layout

| Path | Role |
|------|------|
| `run_app.py` | Starts Uvicorn (`backend.app.main:app`) |
| `backend/app/main.py` | FastAPI entry, CORS, rate limits |
| `backend/app/api_routes_supabase.py` | Document CRUD API |
| `frontend/src` | React + Vite + react-pdf viewer |
| `graphify-out/` | Knowledge graph outputs (local only; see `.gitignore`) |

The old `deploy_stage/` tree was removed; CI and deploy use `backend/` + `frontend/` only.

## Tests

```bash
cd backend
python -m unittest test_embeddings_qa -v
```

Optional API smoke tests (server must be running, credentials in `.env`):

```bash
python verify_api.py
python test_upload.py
```

## Environment highlights

- `USE_SUPABASE=true` — required for production paths
- `CORS_ORIGINS` — comma-separated frontend origins (default `http://localhost:5173`)
- `ALLOW_CLIENT_ID_FALLBACK` — dev only; do not enable in production
- `APP_ENV` / `VITE_APP_ENV` — set to `development` locally and `production` in deploys
- `AUTH_BYPASS_ENABLED` / `VITE_AUTH_BYPASS_ENABLED` — dev-only auth bypass; only works when the matching app env is `development`
- `DEV_AUTH_EMAIL` / `VITE_DEV_AUTH_EMAIL` — local bypass account, default `ysaichaithu2005@gmail.com`
- `TEST_EMAIL` / `TEST_PASSWORD` — for `verify_api.py` / `test_upload.py` only

## Graphify (architecture map)

```bash
python _graphify_build.py   # AST graph from backend/app + frontend/src
```

Outputs: `graphify-out/GRAPH_REPORT.md`, `graph.json`, `graph.html`.

## License

MIT (see `LICENSE` if present).
