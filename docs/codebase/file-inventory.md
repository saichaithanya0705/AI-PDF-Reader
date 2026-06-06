# Maintained File Inventory

This inventory covers maintained source, config, test, and support files in the repository. It intentionally excludes generated caches, databases, logs, archives, `node_modules`, `dist`, `__pycache__`, and Graphify cache outputs.

## Root And Workspace Files

| Path | Purpose |
| --- | --- |
| `.claude/settings.local.json` | local Claude/Codex permission and output-style settings for this workspace |
| `.env.example` | root environment template for backend runtime and shared deployment settings |
| `.gitignore` | ignore rules for env files, caches, logs, data, and generated artifacts |
| `.github/workflows/deploy.yml` | canonical CI and deployment workflow |
| `.github/workflows/main_ai-pdf-reader.yml` | disabled legacy Azure workflow kept as manual-only reference |
| `_graphify_build.py` | script that generates Graphify architecture artifacts |
| `AI_SLOP_AUDIT.md` | repository audit notes focused on AI/code quality concerns |
| `check_models.py` | helper to inspect installed or configured models |
| `db_dump.txt` | database/reference dump artifact stored in the repo |
| `debug_import_path.py` | Python import-path troubleshooting helper |
| `debug_sqlite.py` | SQLite debugging helper |
| `DEPLOY_DIGITALOCEAN.md` | DigitalOcean deployment guide |
| `deploy_backend.sh` | backend deployment/install script |
| `deploy_frontend.sh` | frontend deployment/build script |
| `docs/codebase/README.md` | documentation index for this codebase |
| `docs/codebase/backend.md` | backend subsystem documentation |
| `docs/codebase/frontend.md` | frontend subsystem documentation |
| `docs/codebase/operations.md` | setup, CI/CD, deployment, and workflow documentation |
| `docs/codebase/file-inventory.md` | maintained-file inventory for the repo |
| `exclude.txt` | support file used by repo tooling or filtering steps |
| `graphify-out/GRAPH_REPORT.md` | generated architecture report snapshot |
| `graphify-out/graph.html` | generated Graphify HTML visualization |
| `graphify-out/graph.json` | generated Graphify JSON graph |
| `make_dummy_pdf.py` | helper to generate a sample PDF |
| `mcp.json` | MCP server configuration for local tool integrations |
| `nginx.conf` | main nginx reverse-proxy config |
| `nginx_ssl.conf` | SSL-oriented nginx config variant |
| `pdfapp-backend.service` | systemd unit definition for backend service |
| `PORT_CONFIGURATION.md` | local and production port reference |
| `pytest.ini` | pytest collection and execution configuration |
| `rag_analysis_report.md` | RAG-focused analysis or audit notes |
| `README.md` | top-level quick-start and project overview |
| `requirements.txt` | root dependency delegator to `backend/requirements.txt` |
| `run_app.py` | backend startup script |
| `setup_droplet.sh` | initial host bootstrap script |
| `setup_env.bat` | Windows environment setup helper |
| `setup_services.sh` | service/nginx setup script |
| `test_advanced_rag.py` | ad-hoc RAG test helper |
| `test_output.txt` | stored output artifact from manual testing |
| `test_output_2.txt` | second stored output artifact from manual testing |
| `test_rag.pdf` | sample PDF fixture kept at repo root |
| `update_remote_env.py` | helper to update remote environment settings |
| `upload_to_droplet.bat` | Windows helper to upload code to a droplet |
| `verify_env.py` | environment verification helper |
| `verify_jwt.py` | JWT verification helper |
| `verify_service_key.py` | service-key verification helper |
| `version_check.txt` | stored version/reference artifact at repo root |

## Backend Package And Support Files

| Path | Purpose |
| --- | --- |
| `backend/__init__.py` | backend package marker |
| `backend/.env.example` | backend-focused environment example geared toward deployment |
| `backend/check_genai_env.py` | generative-AI environment verification helper |
| `backend/check_imports.py` | import verification helper |
| `backend/check_jwks.py` | JWKS verification helper |
| `backend/clean_orphaned_entries.py` | cleanup helper for orphaned records/files |
| `backend/fix_database_paths.py` | repair helper for database path issues |
| `backend/migrations/create_chat_history_tables.sql` | SQL migration for chat-history tables in a Supabase/Postgres-style environment |
| `backend/process_documents_for_rag.py` | helper script for RAG backfill or document processing |
| `backend/read_log.py` | log-reading helper |
| `backend/read_run_log.py` | runtime log-reading helper |
| `backend/requirements-minimal.txt` | reduced dependency set for lighter local setup |
| `backend/requirements.txt` | canonical pinned backend dependency list |
| `backend/setup_credentials.py` | Google credential setup helper |
| `backend/test_embedding_fix.py` | ad-hoc embedding verification script |
| `backend/test_embeddings_qa.py` | ad-hoc embeddings QA script |
| `backend/test_gemini_embedding.py` | ad-hoc Gemini embedding test |
| `backend/test_openai_embedding.py` | ad-hoc OpenAI embedding test |
| `backend/test_providers.py` | ad-hoc provider test |
| `backend/test_transformers_availability.py` | ad-hoc transformer availability test |
| `backend/test_transformers_embedding.py` | ad-hoc transformer embedding test |
| `backend/test_upload.py` | ad-hoc upload smoke test |
| `backend/test_vector_search_full.py` | ad-hoc vector-search smoke test |
| `backend/verify_api.py` | manual backend API verification helper |
| `backend/verify_chat.py` | manual chat verification helper |
| `backend/verify_gemini.py` | manual Gemini verification helper |
| `backend/verify_manual.py` | manual verification script |
| `backend/verify_rag_local.py` | local RAG verification helper |
| `backend/version_check.txt` | backend-specific version/reference artifact |

## Backend Application Files

| Path | Purpose |
| --- | --- |
| `backend/app/__init__.py` | backend app package marker |
| `backend/app/auth_config.py` | environment-driven dev-auth bypass rules |
| `backend/app/auth_middleware.py` | live Supabase JWT verification and optional-user helpers |
| `backend/app/chat_history.py` | SQLite-backed chat session and message persistence |
| `backend/app/chat_with_llm.py` | lightweight chat helper for LLM calls |
| `backend/app/chunking_service.py` | canonical adapter from PDF extraction results to chunk records |
| `backend/app/context_builder.py` | prompt/context assembly for library and PDF-viewer chat |
| `backend/app/database.py` | SQLite document metadata, chunk storage, FTS search, and revision tracking |
| `backend/app/document_routes.py` | document CRUD, stats, health, and chat-session router |
| `backend/app/duplicate_cleaner.py` | duplicate PDF detection and cleanup logic |
| `backend/app/duplicate_cleanup_system.py` | cleanup-system wrapper around duplicate handling |
| `backend/app/embedding_service.py` | embedding model loading and batch embedding generation |
| `backend/app/enhanced_llm_service.py` | selected-text insights, related sections, and insight bulb logic |
| `backend/app/generate_audio.py` | alternate provider-based audio generation helper |
| `backend/app/ingestion_service.py` | ingestion orchestration for single docs and collections |
| `backend/app/llm_providers.py` | provider abstraction layer for Gemini, Azure, OpenAI, and Ollama |
| `backend/app/main.py` | FastAPI composition root and non-router API endpoints |
| `backend/app/metadata_extractor.py` | metadata extraction helper |
| `backend/app/middleware/__init__.py` | middleware package marker |
| `backend/app/middleware/auth.py` | alternate or legacy auth middleware implementation |
| `backend/app/middleware/rate_limiter.py` | in-memory rate limiting primitives and examples |
| `backend/app/models.py` | shared Pydantic models for sections, websocket payloads, and relevance |
| `backend/app/pdf_comparator.py` | robust PDF comparison helper |
| `backend/app/pdf_duplicate_detector.py` | lower-level duplicate detection helper |
| `backend/app/pdf_splitter.py` | standalone PDF splitting utility |
| `backend/app/persona_classifier.py` | backend persona/job classification engine |
| `backend/app/rag_service.py` | retrieval, ranking, cache usage, and response generation |
| `backend/app/section_highlighter.py` | section highlighting helpers |
| `backend/app/semantic_cache.py` | semantic cache implementation for retrieval reuse |
| `backend/app/tts_service.py` | runtime TTS provider selection and synthesis |
| `backend/app/user_resolver.py` | effective-user resolution for upload and tenant-aware actions |
| `backend/app/utils/intelligent_pdf_brain.py` | multi-document semantic extraction and insight engine |
| `backend/app/utils/process_pdfs.py` | high-performance single-PDF extraction path |
| `backend/app/vector_store.py` | FAISS vector store and metadata persistence |
| `backend/app/websocket_manager.py` | in-memory WebSocket connection registry |

## Backend Test Suite Files

| Path | Purpose |
| --- | --- |
| `backend/tests/conftest.py` | shared test doubles and fixture scaffolding |
| `backend/tests/test_auth_middleware.py` | auth bypass, JWKS hygiene, and optional-user tests |
| `backend/tests/test_chat_history.py` | SQLite chat persistence tests |
| `backend/tests/test_context_builder.py` | context-building and canonical RAG delegation tests |
| `backend/tests/test_database_revision.py` | library revision and FTS/BM25 tenant-filter tests |
| `backend/tests/test_document_security_routes.py` | route-level tenant and auth security tests |
| `backend/tests/test_embedding_service.py` | embedding-service fail-loud behavior tests |
| `backend/tests/test_enhanced_llm_service.py` | defensive parsing tests for LLM payloads |
| `backend/tests/test_ingestion_service.py` | ingestion metadata schema tests |
| `backend/tests/test_llm_provider_source_hygiene.py` | provider-source hygiene tests |
| `backend/tests/test_main_source_hygiene.py` | source-hygiene tests for `main.py` |
| `backend/tests/test_pdf_rag_pipeline.py` | end-to-end-ish ingestion and RAG pipeline tests |
| `backend/tests/test_rag_service.py` | cache, ranking, and formatting tests for retrieval |
| `backend/tests/test_repository_hygiene.py` | repo and deployment hygiene tests |
| `backend/tests/test_tts_service.py` | TTS configuration and secret-hygiene tests |
| `backend/tests/test_vector_store.py` | FAISS store behavior tests |

## Frontend Package And Config Files

| Path | Purpose |
| --- | --- |
| `frontend/.env.example` | deployment-oriented frontend env example |
| `frontend/.env.local.example` | local-development frontend env example |
| `frontend/eslint.config.js` | frontend lint configuration |
| `frontend/index.html` | Vite HTML entry shell |
| `frontend/package-lock.json` | locked frontend dependency graph |
| `frontend/package.json` | frontend scripts and dependency manifest |
| `frontend/postcss.config.js` | PostCSS configuration |
| `frontend/tailwind.config.js` | Tailwind theme extensions and plugins |
| `frontend/tsconfig.app.json` | TypeScript project config for app code |
| `frontend/tsconfig.json` | top-level TypeScript config |
| `frontend/tsconfig.node.json` | TypeScript config for node-side tooling |
| `frontend/vite.config.ts` | Vite bundler configuration |

## Frontend Public Assets

| Path | Purpose |
| --- | --- |
| `frontend/public/pdf-worker-fallback.js` | fallback PDF worker asset |
| `frontend/public/pdf.min.js` | bundled PDF.js browser asset |
| `frontend/public/pdf.worker.min.js` | PDF.js minified worker asset |
| `frontend/public/pdf.worker.mjs` | ESM PDF.js worker asset |

## Frontend Application Files

| Path | Purpose |
| --- | --- |
| `frontend/src/App.tsx` | app shell with routes and providers |
| `frontend/src/components/AIPersonaJobForm.tsx` | persona/job entry UI using local intent classification |
| `frontend/src/components/ChatHistory.tsx` | chat-session chooser UI |
| `frontend/src/components/CrossDocumentHighlights.tsx` | cross-document highlight presentation component |
| `frontend/src/components/DocumentCard.tsx` | document-card UI for library actions |
| `frontend/src/components/ErrorBoundary.tsx` | top-level React error boundary |
| `frontend/src/components/FloatingInsightsPanel.tsx` | reader-side floating insights surface |
| `frontend/src/components/InsightsNotification.tsx` | transient insights/status UI |
| `frontend/src/components/InsightsPanel.tsx` | alternate or older insights panel |
| `frontend/src/components/PersonaJobForm.tsx` | alternate or older persona/job form |
| `frontend/src/components/PodcastModal.tsx` | podcast generation and playback modal |
| `frontend/src/components/ProtectedRoute.tsx` | auth gate around protected routes |
| `frontend/src/components/RecommendationsPanel.tsx` | recommendations panel component |
| `frontend/src/components/RelatedDocumentsSidebar.tsx` | related-document sidebar in the reader |
| `frontend/src/components/SimpleChatbot.tsx` | library-level chat surface |
| `frontend/src/components/SimplePDFViewer.tsx` | active PDF viewing and selection component |
| `frontend/src/components/SmartPDFViewer.tsx` | wrapper around the active PDF viewer |
| `frontend/src/components/TextSelectionTooltip.tsx` | alternate text-selection analysis UI |
| `frontend/src/components/UploadZone.tsx` | drag/drop upload and validation UI |
| `frontend/src/config.ts` | API and WebSocket URL resolution |
| `frontend/src/context/AuthContext.tsx` | frontend auth state provider |
| `frontend/src/context/PDFContext.tsx` | document state, normalization, and backend integration hub |
| `frontend/src/context/useAuth.ts` | typed auth-context hook |
| `frontend/src/context/usePDF.ts` | typed PDF-context hook |
| `frontend/src/index.css` | global CSS and font imports |
| `frontend/src/lib/api.ts` | authenticated backend client wrapper |
| `frontend/src/lib/devAuth.ts` | development auth-bypass helpers |
| `frontend/src/lib/supabaseClient.ts` | Supabase browser client initialization |
| `frontend/src/main.tsx` | React mount entrypoint |
| `frontend/src/pages/HomePage.tsx` | document library and upload workflow page |
| `frontend/src/pages/LandingPage.tsx` | public marketing and CTA page |
| `frontend/src/pages/LoginPage.tsx` | login page |
| `frontend/src/pages/ReaderPage.tsx` | PDF reader workspace page |
| `frontend/src/pages/SignupPage.tsx` | signup page |
| `frontend/src/utils/networkDetection.ts` | online/offline and Adobe API status helpers |
| `frontend/src/utils/pdfJsInitializer.ts` | alternate local PDF.js initialization helper |
| `frontend/src/utils/pdfValidator.ts` | client-side PDF validation utility |
| `frontend/src/vite-env.d.ts` | Vite environment typing declarations |

## Frontend Test Files

| Path | Purpose |
| --- | --- |
| `frontend/tests/pdf-context-source.test.mjs` | source-shape guard for `PDFContext` and local PDF.js assumptions |

## Notes On Omitted Paths

These repo areas were intentionally not expanded line-by-line here because they are generated or local-state outputs rather than maintained source:

- `frontend/node_modules/`
- `frontend/tsconfig.app.tsbuildinfo`
- `frontend/tsconfig.node.tsbuildinfo`
- `backend/data/`
- `graphify-out/cache/`
- `supabase/.temp/`
- any `__pycache__`, `.pyc`, `.db`, `.sqlite*`, `.log`, `.pkl`, or archive outputs
