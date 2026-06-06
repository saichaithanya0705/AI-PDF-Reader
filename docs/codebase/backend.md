# Backend Documentation

## Overview

The backend is a FastAPI application that serves three roles at once:

- authenticated document-management API
- PDF ingestion, RAG, insight, and TTS execution layer
- optional static host for the built frontend SPA

The runtime entrypoint is `run_app.py`, which starts `uvicorn` against `backend.app.main:app` on `PORT` or `8080`.

## Backend Request Lifecycle

1. `run_app.py` adds the repo root and `backend/` to `sys.path` and starts Uvicorn.
2. `backend/app/main.py` loads `.env`, initializes credentials, sets up directories, builds the FastAPI app, installs CORS and rate limiting, mounts static assets, and includes `document_routes.py`.
3. Authenticated routes depend on `backend/app/auth_middleware.py`.
4. Route handlers fan out into the database, ingestion, RAG, LLM, TTS, or filesystem subsystems.
5. Long-running upload processing emits progress messages through `backend/app/websocket_manager.py`.

## Entrypoints And Routing

### Runtime files

| File | Responsibility |
| --- | --- |
| `run_app.py` | boot script that starts the backend server |
| `backend/app/main.py` | FastAPI app assembly plus upload, RAG, media, websocket, and SPA-serving routes |
| `backend/app/document_routes.py` | `/api` router for document CRUD, stats, health, and chat sessions |

### Route groups

| Concern | Routes | Primary file |
| --- | --- | --- |
| document CRUD | `GET /api/documents`, `GET /api/documents/{document_id}`, `DELETE /api/documents/{document_id}`, `POST /api/documents/{document_id}/update-metadata` | `backend/app/document_routes.py` |
| library/session support | `GET /api/stats`, `GET /api/health`, `POST|GET|DELETE /api/chat/sessions...` | `backend/app/document_routes.py` |
| uploads and transforms | `POST /upload/context_files`, `POST /upload/active_file`, `POST /api/split-document`, `POST /api/merge-documents` | `backend/app/main.py` |
| retrieval and insight | `GET /api/recommendations/{document_id}`, `GET /api/insights/{document_id}`, `POST /api/chat`, `POST /api/ask-gpt`, `POST /api/text-selection-analysis`, `POST /api/ask-gemini-selection`, `GET /api/highlights/{document_id}` | `backend/app/main.py` |
| media | `POST /api/generate-podcast`, `GET /api/audio/{filename}`, `GET|HEAD /api/files/{filename}` | `backend/app/main.py` |
| RAG maintenance | `POST /api/rag/process/{document_id}`, `DELETE /api/rag/document/{document_id}`, `GET /api/library/statistics` | `backend/app/main.py` |
| runtime shell | `GET /`, `GET /config`, `WS /ws/{client_id}`, `GET /{path:path}` | `backend/app/main.py` |

## Storage Model

### Primary application storage

| Storage type | File/module | Purpose |
| --- | --- | --- |
| SQLite documents DB | `backend/app/database.py` | document records, chunk metadata, FTS/BM25 search, duplicate detection metadata, library revision |
| SQLite chat DB | `backend/app/chat_history.py` | chat sessions and chat messages |
| FAISS vector index | `backend/app/vector_store.py` | similarity search across chunk embeddings |
| document files | `backend/data/docs/` created by `backend/app/main.py` | persisted uploaded PDFs |

### Data concepts

- `Document` in `backend/app/database.py` is the main metadata record for stored PDFs.
- `document_chunks` and `document_chunks_fts` hold chunk content and full-text search state.
- `SearchResult` in `backend/app/vector_store.py` is the in-memory retrieval record returned from vector search.
- `backend/app/models.py` defines Pydantic API payloads such as `Section`, `SectionHighlight`, `RelevantSection`, and `WebSocketMessage`.

## Core Subsystems

### App assembly and orchestration

| File | Role |
| --- | --- |
| `backend/app/main.py` | central orchestrator for app initialization and non-router endpoints |
| `backend/app/document_routes.py` | focused router for document and chat-session CRUD |
| `backend/app/websocket_manager.py` | process-local WebSocket connection registry keyed by `client_id` |
| `backend/app/user_resolver.py` | chooses authenticated user id first, then optional `client_id` fallback when explicitly allowed |

### Auth and middleware

| File | Role |
| --- | --- |
| `backend/app/auth_middleware.py` | active Supabase JWT verification path used by the live app |
| `backend/app/auth_config.py` | dev-bypass guardrails driven by `APP_ENV` and `AUTH_BYPASS_ENABLED` |
| `backend/app/middleware/rate_limiter.py` | in-memory rate-limit primitives and helper dependencies |
| `backend/app/middleware/auth.py` | secondary auth implementation that appears to be legacy or reserved, not the live dependency path |

### Storage and retrieval

| File | Role |
| --- | --- |
| `backend/app/database.py` | SQLite persistence and FTS/BM25 search |
| `backend/app/vector_store.py` | FAISS vector store persistence and tenant-aware similarity search |
| `backend/app/semantic_cache.py` | exact and near-duplicate semantic search cache |
| `backend/app/chat_history.py` | chat session storage |

### PDF ingestion and analysis

| File | Role |
| --- | --- |
| `backend/app/ingestion_service.py` | canonical ingestion orchestration for single docs and collections |
| `backend/app/chunking_service.py` | converts PDF extraction results into chunk records |
| `backend/app/utils/process_pdfs.py` | single-PDF title and section extraction |
| `backend/app/utils/intelligent_pdf_brain.py` | multi-PDF semantic extraction and graph-like relevance logic |
| `backend/app/metadata_extractor.py` | metadata extraction helper |
| `backend/app/duplicate_cleaner.py` | duplicate PDF cleanup logic |
| `backend/app/duplicate_cleanup_system.py` | orchestration wrapper around duplicate cleanup |
| `backend/app/pdf_duplicate_detector.py` | duplicate detection helper |
| `backend/app/pdf_comparator.py` | high-confidence PDF comparison helper |
| `backend/app/pdf_splitter.py` | standalone PDF split utility |

### LLM, RAG, and insight layers

| File | Role |
| --- | --- |
| `backend/app/rag_service.py` | retrieval, ranking, cache usage, and RAG answer generation |
| `backend/app/context_builder.py` | shapes viewer and library prompt context |
| `backend/app/enhanced_llm_service.py` | selected-text insight and related-section logic |
| `backend/app/llm_providers.py` | provider abstraction for Gemini, Azure OpenAI, OpenAI, and Ollama |
| `backend/app/chat_with_llm.py` | simple chat helper module |
| `backend/app/persona_classifier.py` | backend persona/job classification module not currently on the main frontend path |
| `backend/app/section_highlighter.py` | highlight calculation and section mapping |
| `backend/app/embedding_service.py` | embedding model loading and batch embedding generation |

### Audio and media

| File | Role |
| --- | --- |
| `backend/app/tts_service.py` | runtime TTS provider selection and synthesis |
| `backend/app/generate_audio.py` | alternate or legacy provider-based audio generation helper |

## Core Pipelines

### 1. Single-document upload and ingestion

1. `backend/app/main.py` validates file bytes and canonicalizes the target filename.
2. The PDF is written under `backend/data/docs/`.
3. A document record is created in `DocumentDatabase`.
4. `DocumentIngestionService.process_document(...)` drives chunking and embedding generation.
5. `ChunkingService.chunk_single_pdf(...)` delegates to `utils/process_pdfs.py`.
6. Chunks are written to SQLite and embeddings to FAISS.
7. Progress is pushed over WebSocket.

### 2. Collection upload and multi-document intelligence

1. `process_pdf_collection(...)` in `backend/app/main.py` starts the collection path.
2. `DocumentIngestionService.process_collection(...)` coordinates the work.
3. `ChunkingService.chunk_collection(...)` uses `IntelligentPDFBrain`.
4. Cross-document semantic content and insights become available to recommendation and viewer flows.

### 3. Retrieval and chat

1. The frontend calls `/api/chat` or another insight endpoint.
2. `RAGService` checks semantic cache first.
3. If needed, the service generates an embedding and queries FAISS.
4. SQLite FTS/BM25 candidates are added.
5. Results are merged, scored, reranked, and formatted.
6. `context_builder.py` or `enhanced_llm_service.py` shapes the final LLM prompt.
7. `llm_providers.py` dispatches to the configured provider.

### 4. Podcast generation

1. `/api/generate-podcast` resolves the document and text to synthesize.
2. `TTSService` selects the configured provider from `tts_service.py`.
3. The audio file is written to disk.
4. `/api/audio/{filename}` serves it back with ownership checks.

## Test Coverage

### Pytest suite under `backend/tests/`

| File | Focus |
| --- | --- |
| `test_document_security_routes.py` | auth and tenant isolation for document and media routes |
| `test_rag_service.py` | cache ordering, ranking, rerank metadata, and error hygiene |
| `test_context_builder.py` | prompt-context composition and canonical service usage |
| `test_auth_middleware.py` | JWT/JWKS handling and dev-bypass rules |
| `test_tts_service.py` | TTS misconfiguration and secret hygiene |
| `test_ingestion_service.py` | canonical vector metadata schema |
| `test_pdf_rag_pipeline.py` | ingestion, extraction, cleanup, and provider contracts |
| `test_vector_store.py` | index deletion behavior, metadata persistence, and filtered search |
| `test_chat_history.py` | SQLite chat persistence |
| `test_database_revision.py` | library revision invalidation and tenant-aware BM25 |
| `test_main_source_hygiene.py` | no mock fallbacks or sensitive leaks in `main.py` |
| `test_enhanced_llm_service.py` | defensive parsing of LLM section outputs |
| `test_embedding_service.py` | fail-loud embedding behavior |
| `test_llm_provider_source_hygiene.py` | provider-source placeholder hygiene |
| `test_repository_hygiene.py` | lockfiles, CI assumptions, deploy hygiene, and repo rules |

### Additional backend scripts

The repo also contains top-level backend smoke or investigation scripts such as `backend/test_upload.py`, `backend/test_vector_search_full.py`, `backend/verify_api.py`, and `backend/verify_rag_local.py`. These are useful for manual verification but are separate from the main `backend/tests/` pytest suite.

## Config And Deployment Notes

- `backend/requirements.txt` is the canonical dependency lock file for the backend.
- `requirements.txt` at the repo root delegates to it so local and CI installs do not drift.
- `deploy_backend.sh` assumes deployment under `/var/www/pdfapp` and refuses to download spaCy models at runtime.
- `.github/workflows/deploy.yml` runs frontend verification plus `python -m pytest backend/tests -q` before deployment.
- `backend/.env.example` documents provider credentials and deployment assumptions, but some variable names drift from live code paths and should not be treated as perfect source of truth.

## Known Inconsistencies And Legacy Paths

- `backend/app/database.py` still contains a legacy `delete_document(...)` and `get_document_metadata(...)` path that references `document_sections`, while the active schema focuses on `document_chunks`.
- `backend/app/auth_middleware.py` is the active auth dependency, while `backend/app/middleware/auth.py` is a parallel implementation that is not wired into `main.py`.
- `backend/app/main.py` reads `CORS_ORIGINS`, while `backend/.env.example` documents `FRONTEND_URL`.
- `backend/migrations/create_chat_history_tables.sql` defines a Supabase/Postgres chat-history schema even though the live runtime uses SQLite chat history.

## Backend Maintenance Guidance

- Treat `backend/app/main.py` as the composition root, not as the place to grow more business logic.
- Prefer `ingestion_service.py`, `rag_service.py`, `context_builder.py`, and `tts_service.py` for subsystem changes.
- Keep auth changes in `auth_middleware.py` and `auth_config.py` unless you intentionally migrate the legacy middleware path.
- If cleaning up legacy code, verify whether any manual scripts still depend on the secondary auth, audio, or database helpers before removing them.
