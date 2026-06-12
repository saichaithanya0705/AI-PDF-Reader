**Verdict**
Score: 31/100, Low slop risk for the scoped auth-bypass and retrieval-cache/BM25 changes after repair
Confidence: Medium

**Why**
- Graphify was read first. The relevant graph hubs for this pass were `DocumentDatabase`, `RAGService`, `apiRequest()`, and the auth/document-route communities around `get_current_user`, `DocumentDatabase`, and frontend API calls.
- The required Graphify scanner reported 35/100 graph-only triage risk and 80/100 source-augmented whole-repo triage risk. The source-wide score is high because the repo still has broad error masking, secret-risk examples, and indirection hotspots, but this hook pass was scoped to code changed in this prompt plus directly connected auth/config architecture.
- Source inspection confirmed one scoped slop-like risk before repair: a development auth bypass could become a production security hole or a partial backend-only shortcut if it were implemented as scattered conditionals.
- Repairs were root-cause changes: one backend auth policy module, production-deny behavior for bypass config, matching frontend development bypass, and tests for the production guard.

**Evidence**
| Signal | Graph Evidence | Source Evidence | Classification | Fix |
|---|---|---|---|---|
| Dev auth bypass could become a production auth hole if implemented ad hoc | Community 1/17 route/auth clusters use `get_current_user`; `apiRequest()` is a frontend hub. | Active protected routes depend on `backend/app/auth_middleware.py`; frontend `ProtectedRoute` and `api.ts` also enforce Supabase session checks. | Confirmed slop signal | Added centralized backend policy in `backend/app/auth_config.py`, wired active auth in `backend/app/auth_middleware.py`, and added tests that production refuses bypass even when `AUTH_BYPASS_ENABLED=true`. |
| Duplicate auth helpers had inconsistent environment semantics | Graphify shows auth/session endpoints as a low-cohesion route cluster; source has both `backend/app/auth_middleware.py` and `backend/app/middleware/auth.py`. | Legacy `require_auth_for_production()` defaulted missing env to development-like behavior. | Confirmed slop signal | Shared `auth_config` from both auth modules and changed production helper to default to `production`. |
| Backend-only bypass would leave frontend login friction and encourage another workaround | `apiRequest()` is a graph hub and protected frontend routes gate the main app. | `frontend/src/context/AuthContext.tsx` required Supabase user, and `frontend/src/lib/api.ts` threw when no Supabase session existed. | Confirmed slop signal | Added `frontend/src/lib/devAuth.ts`; `AuthContext` supplies a deterministic dev user and `api.ts` omits auth headers only in Vite dev with `VITE_APP_ENV=development` and `VITE_AUTH_BYPASS_ENABLED=true`. |
| Retrieval changes from the prompt needed anti-slop verification | `RAGService` and `DocumentDatabase` are graph god nodes. | BM25 retrieval now lives at the database/index boundary and cache exact-hit lookup happens before DB/vector access. | Healthy architecture signal | Tests cover exact cache-before-DB behavior, BM25 tenant filters, BM25-only candidate merge, and revision bump stale-hit prevention. |

**Aggressive Review Targets**
- Repo-wide triage still reports high source-augmented risk, especially broad exception masking in large service modules and credential examples in local `.env`. Those were outside this scoped prompt and should be handled in a separate pass.
- Two auth modules still exist. They now share policy, but long-term cleanup should consolidate route dependencies onto one active auth module and remove the legacy helper once call sites are proven absent.
- `ALLOW_CLIENT_ID_FALLBACK` remains a separate dev-only identity escape hatch. It is not used by the new bypass, but it should eventually be folded into the same auth policy or removed.

**Healthy Signals**
- Development bypass is opt-in and requires both development environment and an explicit bypass flag.
- Production ignores bypass flags and returns `401` without credentials.
- The bypass account is deterministic: `ysaichaithu2005@gmail.com` by default, overridable by explicit dev env.
- Frontend and backend use matching env names and both default to production-safe values.

**Highest-Risk Clusters**
- Auth/config boundary: user identity flows into document ownership and RAG tenant filters. Root cause risk was split policy; repair centralizes backend policy and mirrors only the UI/session affordance in the frontend.
- Retrieval/cache boundary: prior prompt touched graph god nodes. The repaired state keeps BM25 in `DocumentDatabase`, cache policy in `SemanticSearchCache`, and ranking/merge logic in `RAGService`.

**Permanent Fixes**
- Added `backend/app/auth_config.py` as the single backend policy owner for `APP_ENV`, `AUTH_BYPASS_ENABLED`, `DEV_AUTH_EMAIL`, and `DEV_AUTH_USER_ID`.
- Updated active backend auth to accept missing credentials only when the development bypass is explicitly enabled.
- Updated legacy auth helper to share the same bypass and production-default policy.
- Added frontend `devAuth` helper so local protected routes and API calls bypass Supabase only in Vite dev and only when explicitly enabled.
- Documented backend/frontend production and development auth envs in `.env.example`, frontend env examples, and `README.md`.
- Added regression tests for development bypass, production denial, and optional auth.

**Anti-Slop Gates**
- Never add route-level auth bypass conditionals; use `auth_config.auth_bypass_enabled()`.
- Any identity shortcut must prove production-deny behavior with a test.
- Frontend bypass must remain gated by `import.meta.env.DEV` plus `VITE_APP_ENV=development`.
- Do not use `client_id` query parameters as a substitute for authenticated user identity outside explicitly gated development paths.

**Validation**
- Read `graphify-out/GRAPH_REPORT.md` before raw source inspection.
- Ran required triage: `python C:/Users/SAI/.codex/skills/audit-ai-slop/scripts/graphify_slop_scan.py --graphify-out graphify-out --source-root . --format markdown`.
- Red tests observed before implementation: `python -m pytest backend\tests\test_auth_middleware.py` failed for missing dev bypass behavior.
- Validation after fixes:
  - `python -m pytest backend\tests\test_auth_middleware.py` -> 4 passed
  - `python -m pytest backend\tests` -> 43 passed
  - `python -m compileall backend\app` -> passed
  - `cd frontend && npm test` -> 7 passed
  - `cd frontend && npm run build` -> passed, with existing chunk-size/Browserslist warnings
- Process hygiene: checked running recent shell/node processes; no task-created stale terminal or server process remained.
- Residual risk: Graphify output is dated 2026-05-17 and predates these repairs, so confidence remains Medium until the graph is regenerated.

---

## Scoped AI Slop Audit - Bulk Library Upload Contract (2026-06-12)

**Verdict**
Score: 18/100, Minimal slop risk for the scoped bulk-upload contract after repair
Confidence: Medium

**Why**
- Graphify was read first. The relevant graph targets for this pass were `apiRequest()` in Community 8, `PDFProvider()` in Community 13, and document/library routes in Community 12.
- The required Graphify scanner reports a severe whole-repo source-augmented triage score, but the hits are dominated by unrelated backend hubs, secrets in environment files, broad exception masking, and existing frontend hotspots outside this upload-contract scope.
- Source inspection confirmed one slop-like risk in the new upload contract: document library seeding trusted `jobId` alone and did not explicitly reject failed/error file rows.
- The repair was a root-cause contract fix: normalize status at the upload boundary and exclude failed/error rows before creating document seeds, with regression coverage for a failed row that still carries a stray `job_id`.

**Evidence**
| Signal | Graph Evidence | Source Evidence | Classification | Likely Root Cause | Permanent Fix | Prevention Gate |
|---|---|---|---|---|---|---|
| Bulk-upload library state could accept failed rows if they carried `job_id` | Community 8 includes frontend API helpers around `apiRequest()`; Community 13 includes `PDFProvider()` and `usePDF()`; Community 12 covers library document routes. | `frontend/src/context/bulkUploadContract.ts` now normalizes status and rejects `failed`, `error`, and error-bearing rows before seed creation; `frontend/tests/pdf-context-source.test.mjs` now verifies a failed row with `job_id: 'doc-broken'` is excluded. | Confirmed slop signal, repaired | The first upload-contract fix removed legacy arrays but left a happy-path assumption that backend failed records would never include ids. | Added status normalization, explicit failed/error filtering in `getBulkUploadedDocumentSeeds()`, and UI failed-count parity in `HomePage.tsx`. | Contract tests must include malformed-but-plausible per-file rows, not only the backend happy path. |
| Whole-repo Graphify/source triage remains high outside this scope | Scanner: graph-only 35/100, source-augmented 95/100; top hotspots include `backend/app/main.py`, `backend/app/llm_providers.py`, `backend/app/rag_service.py`, and `frontend/src/pages/HomePage.tsx`. | Unrelated dirty files and scanner hits remain outside the bulk-upload edit set. | Aggressive review target | Existing repo-wide governance and architecture debt is broader than this hook pass. | Keep this pass scoped; schedule separate audits for backend hubs, secrets, and broad exception masking. | Regenerate Graphify after major repairs and require narrower subsystem audits before merging unrelated work. |

**Aggressive Review Targets**
- `frontend/src/pages/HomePage.tsx` remains a large page component with upload-progress behavior outside this audit scope. This audit fixed only the bulk-upload failure-count contract path.
- `frontend/tests/pdf-context-source.test.mjs` contains unrelated chat-history source guards in the working tree. They were preserved and not treated as evidence for this upload-contract audit.
- Whole-repo scanner findings around environment secrets, broad exception masking, and backend god nodes remain unresolved outside this scope.

**Healthy Signals**
- The backend `/upload/context_files` auth-scoped contract remains intact; no backend auth or `client_id` fallback behavior was changed.
- Upload parsing is centralized in `frontend/src/context/bulkUploadContract.ts` rather than duplicated in `PDFContext` and `HomePage`.
- Tests exercise the backend `files` array shape, duplicate rows, failed rows, status normalization, and library seed exclusion.

**Workflow Gaps**
- The Graphify snapshot is dated `2026-05-17`, so it predates the upload-contract commit and this repair.
- Frontend tests still rely partly on source-inspection guards. The executable contract tests are stronger, but component-level provider tests would raise confidence.

**Highest-Risk Clusters**
- Bulk upload state boundary: `upload/context_files` returns mixed per-file outcomes, while frontend library state must only persist accepted or duplicate documents. The risk was treating a loosely present id as success.

**Likely Root Causes**
- Contract migration bias: the original fix correctly moved from `job_ids`/`file_urls` to `files`, but did not fully encode the status/error invariant at the document-seed boundary.
- Happy-path fixture bias: the initial failed-row test omitted `job_id`, matching current backend behavior but not proving the frontend guard.

**Permanent Fixes**
- Normalized bulk upload status values in `frontend/src/context/bulkUploadContract.ts`.
- Excluded failed/error rows from `getBulkUploadedDocumentSeeds()` even when a row has a `jobId`.
- Updated the HomePage failed-count logic to match explicit failed/error semantics.
- Strengthened the contract test with a failed row that includes `job_id`.

**Anti-Slop Gates**
- Treat per-file upload status as the source of truth for library persistence.
- Test malformed but plausible API rows at frontend contract boundaries.
- Keep upload response parsing in the contract module; do not reintroduce parallel array assumptions or caller-local parsing.

**Validation**
- Read `graphify-out/GRAPH_REPORT.md` before raw source inspection.
- Ran required triage: `python C:/Users/SAI/.codex/skills/audit-ai-slop/scripts/graphify_slop_scan.py --graphify-out graphify-out --source-root . --format markdown`.
- Validation after repair:
  - `cd frontend && npm test` -> 14 passed
  - `cd frontend && npm run build` -> passed, with existing Browserslist, plugin timing, and chunk-size warnings
  - `cd frontend && npx tsc -p tsconfig.app.json --noEmit` -> failed on pre-existing unrelated strict-mode issues in `AIPersonaJobForm.tsx`, `ErrorBoundary.tsx`, `FloatingInsightsPanel.tsx`, `HomePage.tsx` fallback-localStorage code, `networkDetection.ts`, and `pdfJsInitializer.ts`; no reported errors were in the bulk-upload contract files.
