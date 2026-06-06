# AI PDF Reader

AI PDF Reader is a full-stack PDF intelligence platform built for the Adobe Hackathon Finale. It combines a React PDF reading experience with a FastAPI backend that can upload, index, search, summarize, compare, split, merge, and discuss documents through retrieval-augmented generation.

The application is designed around authenticated document libraries. Users sign in with Supabase, upload PDFs, read them in a browser-based viewer, ask contextual questions, surface related sections across documents, generate insights, and create audio or podcast-style summaries from document content.

## Core Features

- **Authenticated PDF library** with Supabase session handling and per-user document access.
- **Smart PDF upload pipeline** for active documents and context documents, including validation, metadata extraction, duplicate handling, and background processing.
- **RAG chat** across a user's document library using chunking, embeddings, vector search, and context-aware prompt construction.
- **Intelligent reader view** with PDF.js rendering, related documents, text-selection analysis, section highlights, recommendations, and insights.
- **Document operations** for listing, updating metadata, soft deletion, split, merge, statistics, and RAG reprocessing.
- **LLM provider abstraction** supporting Gemini, Azure OpenAI, OpenAI, and Ollama-style local providers.
- **Text-to-speech and podcast generation** through Azure, Google, or local fallback providers.
- **WebSocket upload progress** so the frontend can show processing status for long-running document jobs.

## Architecture

```text
React + Vite frontend
  -> Supabase auth session or guarded development bypass
  -> Authenticated API requests through frontend/src/lib/api.ts
  -> PDF.js / react-pdf reader and document workflow UI
  -> WebSocket progress updates during upload and processing

FastAPI backend
  -> Auth middleware and rate limiting
  -> Document CRUD routes and chat history routes
  -> PDF validation, extraction, section detection, and metadata parsing
  -> Chunking, embeddings, vector store, and RAG orchestration
  -> LLM providers for chat, recommendations, summaries, and insights
  -> TTS providers for audio and podcast generation

Storage and services
  -> Supabase for authentication and production document metadata paths
  -> Local runtime data under backend/data for generated files and indexes
  -> FAISS / vector-store metadata for retrieval workflows
```

## Repository Layout

| Path | Purpose |
| --- | --- |
| `run_app.py` | Local backend startup script for `backend.app.main:app`. |
| `backend/app/main.py` | FastAPI application, upload routes, RAG/chat endpoints, reader utilities, and static serving fallback. |
| `backend/app/document_routes.py` | Document CRUD, statistics, and chat-session API routes. |
| `backend/app/ingestion_service.py` | PDF ingestion, chunk persistence, embedding generation, and vector indexing coordination. |
| `backend/app/rag_service.py` | Retrieval-augmented generation service for document-aware answers. |
| `backend/app/context_builder.py` | Builds library and PDF-viewer context for chatbot interactions. |
| `backend/app/llm_providers.py` | Provider abstraction for Gemini, Azure OpenAI, OpenAI, and Ollama. |
| `backend/app/tts_service.py` | Text-to-speech provider abstraction and audio generation support. |
| `frontend/src/App.tsx` | Frontend route shell for landing, auth, library, and reader pages. |
| `frontend/src/context` | Auth and PDF state providers used by the frontend. |
| `frontend/src/components` | Upload, reader, chat, recommendation, insights, and document UI components. |
| `frontend/src/lib/api.ts` | Centralized frontend API client and auth header handling. |
| `docs/codebase` | Deeper backend, frontend, operations, and file-inventory documentation. |
| `graphify-out/GRAPH_REPORT.md` | Generated architecture graph summary used for codebase navigation. |

## Runtime Requirements

- Python 3.10 or newer is recommended.
- Node.js 20 or newer is recommended for the Vite frontend.
- Supabase project credentials for production-style auth and storage paths.
- At least one LLM provider key or local provider:
  - Gemini via `GOOGLE_API_KEY`
  - Azure OpenAI via Azure OpenAI environment variables
  - OpenAI via `OPENAI_API_KEY`
  - Ollama via local Ollama configuration

## Local Setup

1. Create backend environment values:

   ```bash
   copy .env.example .env
   ```

   Fill in Supabase credentials and one LLM provider. For local development, set:

   ```env
   APP_ENV=development
   CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```

2. Create frontend environment values:

   ```bash
   copy frontend\.env.example frontend\.env.local
   ```

   For local backend development:

   ```env
   VITE_APP_ENV=development
   VITE_API_URL=http://127.0.0.1:8080
   VITE_SUPABASE_URL=your_supabase_project_url
   VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

3. Install backend dependencies:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r backend\requirements.txt
   ```

   For a lighter local install, use `backend/requirements-minimal.txt` where supported.

4. Install frontend dependencies:

   ```bash
   cd frontend
   npm ci
   cd ..
   ```

5. Start the backend:

   ```bash
   python run_app.py
   ```

   The API runs at `http://127.0.0.1:8080`.

6. Start the frontend in another terminal:

   ```bash
   cd frontend
   npm run dev
   ```

   The app runs at `http://localhost:5173`.

## Main Application Routes

Frontend routes:

| Route | Description |
| --- | --- |
| `/` | Landing page. |
| `/login` | Supabase sign-in page. |
| `/signup` | Supabase sign-up page. |
| `/library` | Protected document library and upload workflow. |
| `/reader/:pdfId` | Protected PDF reader and AI workspace. |

Backend routes include:

| Endpoint | Purpose |
| --- | --- |
| `POST /upload/active_file` | Upload the primary PDF for a reader workflow. |
| `POST /upload/context_files` | Upload supporting PDFs for cross-document context. |
| `WS /ws/{client_id}` | Stream upload and processing progress. |
| `GET /api/documents` | List authenticated user's documents. |
| `GET /api/documents/{document_id}` | Fetch a specific document record. |
| `DELETE /api/documents/{document_id}` | Delete a document record. |
| `POST /api/chat` | Ask library-aware or PDF-aware chatbot questions. |
| `POST /api/ask-gpt` | Ask a contextual question against selected PDF context. |
| `POST /api/text-selection-analysis` | Analyze selected text from the reader. |
| `GET /api/recommendations/{document_id}` | Get related document recommendations. |
| `GET /api/insights/{document_id}` | Generate document insights. |
| `POST /api/generate-podcast` | Generate an audio summary or podcast artifact. |
| `POST /api/rag/process/{document_id}` | Reprocess a document for RAG indexing. |

## Environment Variables

Important backend values:

| Variable | Notes |
| --- | --- |
| `APP_ENV` | Use `development` locally and `production` in deployed environments. |
| `USE_SUPABASE` | Enables Supabase-backed production paths. |
| `SUPABASE_URL` | Supabase project URL. |
| `SUPABASE_SERVICE_KEY` | Server-only service role key. Never expose this to the frontend. |
| `SUPABASE_JWT_SECRET` | Used for JWT verification. |
| `CORS_ORIGINS` | Comma-separated frontend origins allowed by the API. |
| `LLM_PROVIDER` | One of `gemini`, `azure`, `openai`, or `ollama`. |
| `GOOGLE_API_KEY` | Gemini API key when `LLM_PROVIDER=gemini`. |
| `TTS_PROVIDER` | Optional TTS provider, such as `azure` or local fallback. |
| `AUTH_BYPASS_ENABLED` | Development-only auth bypass; ignored outside development. |
| `ALLOW_CLIENT_ID_FALLBACK` | Development-only upload fallback; keep disabled in production. |

Important frontend values:

| Variable | Notes |
| --- | --- |
| `VITE_APP_ENV` | Frontend runtime environment. |
| `VITE_API_URL` | Backend API origin, for example `http://127.0.0.1:8080`. |
| `VITE_SUPABASE_URL` | Supabase project URL exposed to the browser. |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon public key. Do not use the service role key here. |
| `VITE_AUTH_BYPASS_ENABLED` | Development-only auth bypass flag. |

## AI System Safety Notes

The backend treats LLM output as probabilistic, not deterministic. Provider calls are routed through service layers that can validate responses, apply fallbacks, and keep side effects separate from generated text. Any new AI-facing feature should preserve that pattern: parse defensively, log enough context for debugging, validate before file or database writes, and retry provider failures where the user workflow can tolerate it.

## Testing

Backend tests:

```bash
python -m pytest backend/tests
```

Frontend tests:

```bash
cd frontend
npm test
```

Frontend lint:

```bash
cd frontend
npm run lint
```

Backend API smoke tests require the server to be running and credentials in `.env`:

```bash
python backend\verify_api.py
python backend\test_upload.py
```

## Deployment Notes

The repository includes deployment helpers for DigitalOcean, Render-style backend hosting, Netlify-style frontend hosting, Nginx, and a systemd backend service. Treat `.env.example`, `frontend/.env.example`, `DEPLOY_DIGITALOCEAN.md`, `deploy_backend.sh`, `deploy_frontend.sh`, `nginx.conf`, and `pdfapp-backend.service` as deployment references rather than one universal production path.

Production checklist:

- Set `APP_ENV=production` and `VITE_APP_ENV=production`.
- Keep `AUTH_BYPASS_ENABLED=false` and `VITE_AUTH_BYPASS_ENABLED=false`.
- Keep `ALLOW_CLIENT_ID_FALLBACK=false`.
- Configure exact deployed frontend origins in `CORS_ORIGINS`.
- Store service role keys only in backend secrets.
- Use the Supabase anon key only in frontend environment variables.
- Verify file storage, generated audio paths, and RAG index persistence for the chosen host.

## Development Notes

- Generated runtime data is intentionally ignored by Git, including `backend/data`, local databases, vector indexes, caches, logs, and local `.env` files.
- The architecture graph can be rebuilt with:

  ```bash
  python _graphify_build.py
  ```

- For deeper codebase details, start with `docs/codebase/README.md`.

## License

No license file is currently present in this repository. Add one before distributing the project publicly if reuse terms need to be explicit.
