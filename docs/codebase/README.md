# Codebase Documentation

This repository is an AI-assisted PDF reading platform with a React/Vite frontend and a FastAPI backend. The system accepts PDF uploads, stores document metadata locally in SQLite, indexes chunks in FAISS, authenticates users with Supabase JWTs, and exposes RAG, insight, podcast, and document-management workflows over HTTP and WebSocket.

## What This Documentation Covers

- `docs/codebase/backend.md`: backend runtime, routes, storage, pipelines, and tests
- `docs/codebase/frontend.md`: frontend routing, state model, pages, components, and browser-side utilities
- `docs/codebase/operations.md`: setup, environment, CI/CD, deployment, support scripts, and known repo drift
- `docs/codebase/file-inventory.md`: maintained-file inventory for the repo, grouped by area

## Architecture At A Glance

```text
Browser (React + Vite + Tailwind)
  -> Supabase auth session / dev auth bypass
  -> Authenticated HTTP calls to FastAPI
  -> WebSocket status updates for upload jobs

FastAPI backend
  -> SQLite document metadata + chunk storage
  -> SQLite chat history
  -> FAISS vector index + JSON metadata
  -> PDF extraction and chunking pipeline
  -> LLM provider abstraction (Gemini / Azure OpenAI / OpenAI / Ollama)
  -> TTS provider abstraction (Azure / Google / local helper paths)
```

## Source Of Truth

- Backend entrypoint: `run_app.py`
- Backend app assembly: `backend/app/main.py`
- Backend document router: `backend/app/document_routes.py`
- Frontend app shell: `frontend/src/App.tsx`
- Frontend state hubs: `frontend/src/context/AuthContext.tsx`, `frontend/src/context/PDFContext.tsx`
- Canonical backend dependencies: `backend/requirements.txt`
- Canonical frontend package manifest: `frontend/package.json`
- Canonical CI/deploy workflow: `.github/workflows/deploy.yml`
- Architecture graph snapshot: `graphify-out/GRAPH_REPORT.md`

## Major Runtime Flows

### 1. Authenticated library usage

1. The browser signs in through Supabase or uses the dev bypass path.
2. `frontend/src/lib/api.ts` attaches the JWT to backend API calls unless bypass mode is enabled.
3. `backend/app/auth_middleware.py` verifies the token and resolves the effective user for route handlers.

### 2. PDF upload and ingestion

1. The library UI uploads active or context files through `/upload/active_file` or `/upload/context_files`.
2. `backend/app/main.py` validates the PDF, writes it under `backend/data/docs`, creates a document record, and starts background processing.
3. `backend/app/ingestion_service.py` coordinates chunking, embedding generation, SQLite chunk persistence, and FAISS index writes.

### 3. Retrieval and chat

1. The frontend invokes `/api/chat`, `/api/recommendations/{document_id}`, `/api/insights/{document_id}`, or `/api/text-selection-analysis`.
2. `backend/app/rag_service.py` combines semantic cache hits, embeddings, vector search, BM25/FTS search, and reranking.
3. `backend/app/context_builder.py` and `backend/app/enhanced_llm_service.py` shape prompts and enrichment payloads.

### 4. Reader-side media generation

1. The reader requests a podcast or audio experience.
2. `backend/app/tts_service.py` selects the configured provider.
3. The backend serves protected media back through `/api/audio/{filename}`.

## Key Cross-Cutting Design Choices

- User auth is Supabase-based, but primary application data is stored locally in SQLite plus FAISS rather than in Supabase tables.
- The backend serves the SPA when `frontend/dist` exists, so local full-stack deploys can run from one process and one web root.
- Persona/job classification on the frontend is currently local keyword logic inside `PDFContext`, even though the backend also contains a richer `persona_classifier.py`.
- The codebase contains both active paths and legacy/parallel implementations. The deeper docs call these out explicitly so maintainers know what is actually wired into runtime.

## Generated Vs. Maintained Artifacts

The maintained-file inventory intentionally documents source, config, test, and support files. It does not enumerate generated or local-machine artifacts such as:

- `frontend/node_modules/`
- `backend/__pycache__/`, `backend/app/__pycache__/`
- `.pyc`, `.db`, `.sqlite*`, `.pkl`, log files
- `graphify-out/cache/`
- frontend `dist/` output
- `supabase/.temp/` CLI temp metadata

Those directories still matter operationally, but they are outputs or local state rather than authored code.
