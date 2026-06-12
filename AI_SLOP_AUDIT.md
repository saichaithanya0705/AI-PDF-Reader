**Verdict**
Score: 16/100, Minimal slop risk for the scoped authenticated chat-history/session changes after repair
Confidence: Medium

**Why**
- Graphify was read first. The relevant graph targets for this pass were `apiRequest()` as a frontend hub plus Communities 1 and 17, which cover chat-session routes and `ChatHistoryManager`.
- The required Graphify scanner still reports severe whole-repo triage risk, but that result is dominated by unrelated broad exception masking, secret examples, and large pre-existing hotspots outside this prompt. This audit is scoped to the chat-history changes made in this prompt and the directly connected backend/frontend session contract.
- Source inspection confirmed that the touched chat flow had low-trust AI-slop patterns before repair: duplicated session contract definitions, unvalidated payload boundaries, dead compatibility transport, and a stale-session reuse path after deletion.
- The repairs were root-cause fixes rather than patches: explicit backend response models, centralized frontend response parsing, stricter request validation, removal of unused transport fields, and regression tests for authenticated session ownership and schema enforcement.

**Evidence**
| Signal | Graph Evidence | Source Evidence | Classification | Likely Root Cause | Permanent Fix | Prevention Gate |
|---|---|---|---|---|---|---|
| Chat-session contract was duplicated and weakly typed across backend routes and frontend consumers | Community 1 contains `create_chat_session_endpoint()`, `list_chat_sessions_endpoint()`, `get_chat_session_endpoint()`, and `delete_chat_session_endpoint()`; Community 17 centers `ChatHistoryManager`; `apiRequest()` is a top frontend hub. | `backend/app/document_routes.py:275`, `backend/app/document_routes.py:308`, `backend/app/document_routes.py:342`, and `backend/app/document_routes.py:378` used generic `Dict[str, Any]` response models; `frontend/src/lib/api.ts:320` and `frontend/src/lib/api.ts:332` now centralize contract parsing that was previously scattered in UI components. | Confirmed slop signal | Solution-first edits added typed-looking annotations without a single validating owner for the session payload. | Added explicit FastAPI response models for chat-session routes and centralized frontend parsers for list/detail/delete responses. | Keep backend chat-session responses on named Pydantic models and keep all frontend chat-session parsing in `api.ts`. |
| The chat send path still carried dead compatibility transport and stale request indirection | `apiRequest()` is a graph god node, so extra chat transport fields spread review burden quickly. | `frontend/src/lib/api.ts:356` and `frontend/src/lib/api.ts:486` now define a single `sendChatMessage()` contract and no longer send `document_context`; the source guard at `frontend/tests/pdf-context-source.test.mjs:89` verifies that stale transport stays removed. | Confirmed slop signal | Fear of breaking callers led to a compatibility shim even though no active caller used it. | Removed the overloaded legacy helper path and the backend-unused `document_context` payload field. | Do not preserve transport fields or overloads without an active caller or a verified backend consumer. |
| Request validation on the chat boundary allowed drift between frontend assumptions and backend acceptance | Community 1 is the authenticated route cluster; Graphify marks it low-cohesion, which raises the value of explicit contract enforcement. | `backend/app/main.py:1636` now constrains `context_type` with `Literal["library", "pdf_viewer"]` and uses `Field(default_factory=list)` for `conversation_history`; `backend/tests/test_document_security_routes.py:290` verifies invalid `context_type` returns `422`. | Confirmed slop signal | The original request model used a free-form string and mutable default list, which makes API drift easy and failures harder to localize. | Tightened request schema with `Literal` and `Field(default_factory=list)`. | Treat chat request fields as an API contract, not a permissive bag of values. |
| Deleted or unauthorized sessions could remain active in the client flow | Graphify’s inferred edge `chat_endpoint() -> get_chat_history_manager()` made the session lifecycle boundary worth verifying in source. | `backend/app/main.py:1677` revalidates `request.session_id` against the authenticated user before reuse; `frontend/src/components/SimpleChatbot.tsx:271` and `frontend/src/components/SimpleChatbot.tsx:280` reset client state when the active session is deleted; `backend/tests/test_document_security_routes.py:237` verifies authenticated list/load/delete ownership. | Confirmed slop signal | The UI and chat endpoint both assumed the session identifier remained valid after history mutations. | Revalidated `session_id` server-side and cleared stale active-session state client-side after delete. | Any stateful chat identifier must be rechecked at the backend boundary and invalidated in the UI when ownership changes. |

**Aggressive Review Targets**
- The whole-repo scanner still reports broad exception masking and secret-risk hits in unrelated modules. Those are real review targets, but they are outside this prompt’s chat-session scope.
- `backend/app/main.py` remains a large hub and still deserves a separate architectural decomposition pass. This repair only tightened the chat request/session boundary inside that file.
- `frontend/src/lib/api.ts` is still a broad client hub. The new chat parsing is centralized there intentionally, but a later cleanup could split domain-specific helpers into a dedicated authenticated chat API module if the repo adopts that pattern consistently.

**Healthy Signals**
- Chat-session ownership is now tested end-to-end on the authenticated routes.
- Invalid `context_type` is rejected by the backend instead of being normalized heuristically in the UI.
- The frontend no longer re-validates session payloads ad hoc inside `ChatHistory` and `SimpleChatbot`; the boundary now has one parsing owner.
- Deleting the active chat session no longer leaves the chatbot pinned to a stale `sessionId`.

**Workflow Gaps**
- The Graphify report is dated `2026-05-17`, so the structural graph view predates these repairs.
- The repository still relies heavily on source-inspection tests on the frontend. They are useful as architecture guards, but they do not replace runtime component tests.

**Highest-Risk Clusters**
- Authenticated chat-session boundary: backend route schema, chat endpoint reuse, and frontend session consumers all touched the same identity-bearing payloads. The root cause was contract duplication without one validating owner.
- Frontend transport hub: `api.ts` is a shared boundary, so stale fields and weak parsing there become repo-wide maintenance risk quickly.

**Likely Root Causes**
- Context starvation during earlier chat-history work: route additions, UI fixes, and session-state changes were made in separate files without consolidating the shared contract first.
- Over-trust in typed annotations: `Dict[str, Any]` and interface annotations made the flow look structured even when the runtime boundary was still permissive.
- Compatibility bias: stale fields and overloads were kept “just in case” instead of being proven necessary.

**Permanent Fixes**
- Added named response models for authenticated chat-session routes in `backend/app/document_routes.py`.
- Tightened `ChatRequest` in `backend/app/main.py` with `Literal` context typing and `Field(default_factory=list)` for history.
- Centralized chat-session and chat-response parsing in `frontend/src/lib/api.ts`.
- Removed the backend-unused `document_context` chat transport field and the unused overload-based `sendChatMessage` compatibility shim.
- Simplified `ChatHistory` and `SimpleChatbot` so they consume validated chat payloads instead of reinterpreting raw API shapes.
- Added regression coverage for route ownership, invalid `context_type`, and the new frontend architecture guards.

**Anti-Slop Gates**
- Do not return `Dict[str, Any}` for authenticated chat endpoints when the payload shape is stable enough to model explicitly.
- Do not add UI-level payload normalization when the shared API layer can own that validation once.
- Remove stale transport fields as soon as no verified backend consumer exists.
- Add a test whenever a chat-state mutation changes ownership, identifier lifetime, or schema guarantees.

**Validation**
- Read `graphify-out/GRAPH_REPORT.md` before raw source inspection.
- Ran required triage: `python C:/Users/SAI/.codex/skills/audit-ai-slop/scripts/graphify_slop_scan.py --graphify-out graphify-out --source-root . --format markdown`.
- Validation after repair:
  - `python -m pytest backend/tests/test_document_security_routes.py backend/tests/test_chat_history.py` -> 10 passed
  - `cd frontend && npm test` -> 12 passed
  - `cd frontend && npm run build` -> passed, with existing Browserslist and chunk-size warnings
- Residual risk:
  - The whole-repo Graphify scanner still reports high unrelated risk outside this prompt.
  - The graph snapshot predates these repairs, so confidence is Medium rather than High until Graphify is regenerated.

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

---

## Scoped AI Slop Audit - Production Login and Upload Progress Runtime Fixes (2026-06-12)

**Verdict**
Score: 14/100, Minimal slop risk for the scoped production login and upload-progress fixes after repair
Confidence: Medium

**Why**
- Graphify was read first. The relevant graph targets for this pass were `apiRequest()` and frontend API helpers in Community 8, auth UI flows in Community 18, and the `HomePage` upload surface connected to document processing.
- The required Graphify scanner still reports severe whole-repo source-augmented triage risk, but the broad hits are dominated by unrelated backend hubs, local environment secret-risk findings, broad exception masking, and pre-existing frontend hotspots outside this prompt's production-login/upload-progress scope.
- Source inspection confirmed two slop-like risks in the changed surface: upload WebSocket protocol parsing lived inside a broad page component with shallow source-string tests, and auth network failures were surfaced as raw provider/browser text instead of a stable auth-boundary message.
- The repair was root-cause oriented: upload progress now has a single pure parser module with executable contract tests, and login/signup share one auth error translation boundary instead of duplicating catch-block interpretation.

**Evidence**
| Signal | Graph Evidence | Source Evidence | Classification | Likely Root Cause | Permanent Fix | Prevention Gate |
|---|---|---|---|---|---|---|
| Upload progress rendering previously depended on an undeclared state variable and page-local WebSocket parsing | Graphify marks `frontend/src/pages/HomePage.tsx` as part of a large frontend surface and flags `apiRequest()`/frontend helpers as hubs; large page-level protocol code increases review risk. | `frontend/src/pages/HomePage.tsx:30` now imports the parser/type from `frontend/src/lib/uploadProgress.ts`; `frontend/src/pages/HomePage.tsx:136` declares `uploadProgress`; `frontend/src/pages/HomePage.tsx:216` consumes `normalizeUploadSocketMessage(message)`. | Confirmed slop signal, repaired | A UI edit added progress rendering without first establishing a durable state/protocol owner. | Declared `UploadProgressState` and moved backend WebSocket normalization into `frontend/src/lib/uploadProgress.ts`. | Keep backend message parsing in a pure boundary module; page components should render normalized state, not define protocol contracts inline. |
| Upload WebSocket contract coverage was shallow and source-string based | Scanner reported shallow-test/mock and verification-debt patterns repo-wide; this prompt added a source-inspection test in that risk category. | `frontend/tests/homepage-upload-progress.test.mjs:32` loads the parser directly; `frontend/tests/homepage-upload-progress.test.mjs:53`, `:75`, and `:94` execute progress, completion-alias, unknown-event, and error payload cases. | Confirmed slop signal, repaired | The first regression test guarded implementation text rather than backend payload behavior. | Added executable parser tests using the repo's existing TypeScript transpile/VM test pattern. | Boundary tests must execute normalization logic and include malformed-but-plausible payloads. |
| Raw auth/network failures were shown directly to users during login/signup | Graphify Community 18 covers `signIn`, `signUp`, `ProtectedRoute`, and login submit flows, making duplicated catch-block behavior a contract risk. | `frontend/src/lib/authErrors.ts:8` defines the stable auth service outage message; `frontend/src/pages/LoginPage.tsx:44` and `frontend/src/pages/SignupPage.tsx:48` both call `toAuthErrorMessage(err)`. | Confirmed slop signal, repaired | Provider/browser errors were treated as user-facing copy, so production config outages surfaced as "Failed to fetch". | Centralized auth error translation and reused it from both login and signup submit flows. | Auth UI catch blocks should call the shared translator; do not surface raw network/provider messages directly. |
| Production `/config` could be masked by SPA fallback if nginx did not proxy it before static routing | Community 8 includes config/API helpers that depend on runtime backend config; production routing must preserve that boundary. | `nginx_ssl.conf:22` proxies `/config` to the backend before the static `location /` block at `nginx_ssl.conf:31`. | Confirmed deployment-boundary issue, repaired | Runtime config was treated like frontend static routing instead of a backend API boundary. | Added a dedicated `/config` proxy location and validated nginx syntax during deployment. | Keep runtime config endpoints out of SPA fallback routing and validate nginx config before reload. |

**Aggressive Review Targets**
- `frontend/src/pages/HomePage.tsx` remains a broad page component. This pass removed upload protocol parsing from it, but a later `useUploadProgressSocket` hook could further isolate WebSocket lifecycle concerns.
- Whole-repo scanner findings around local environment secrets, broad exception masking, and backend god nodes remain unresolved outside this scoped pass. Secret values were not reproduced in this report.
- The Graphify snapshot is dated before these repairs, so structural confidence remains Medium until Graphify is regenerated.

**Healthy Signals**
- Production login was tested against the deployed HTTPS site after redeployment and redirected to `/library` without the `uploadProgress is not defined` runtime error.
- Auth outage messaging now has one owner instead of separate login/signup catch-block text.
- Upload progress parser behavior is now executable in tests and clamps/normalizes backend percent, completion aliases, unknown events, and error payloads.

**Workflow Gaps**
- Frontend tests still include several source-inspection guards in other files. This pass fixed the new upload-progress test because it was in the changed surface.
- `npm run build` still reports existing Browserslist/plugin timing/chunk-size warnings. They are not regressions from this pass, but chunking deserves a separate performance cleanup.

**Permanent Fixes**
- Added `frontend/src/lib/uploadProgress.ts` as the single upload WebSocket progress parser.
- Updated `HomePage` to import the parser and keep only UI/WebSocket lifecycle responsibilities.
- Converted the upload-progress regression coverage from string-only checks to direct parser behavior tests.
- Added `frontend/src/lib/authErrors.ts` and wired login/signup to the shared auth error translator.
- Added the production nginx `/config` proxy before the SPA static fallback.

**Anti-Slop Gates**
- Do not add page-local protocol parsers for backend event streams when a pure boundary module can own validation.
- Do not add source-only tests for new contract code when the module can be executed by the existing test runner.
- Do not expose raw provider/browser network errors as final user-facing auth messages.
- Do not route runtime backend config through frontend SPA fallback.

**Validation**
- Read `graphify-out/GRAPH_REPORT.md` before raw source inspection.
- Ran required triage: `python C:/Users/SAI/.codex/skills/audit-ai-slop/scripts/graphify_slop_scan.py --graphify-out graphify-out --source-root . --format markdown`.
- Validation after repair:
  - `cd frontend && npm test` -> 17 passed
  - `cd frontend && npm run build` -> passed, with existing Browserslist, plugin timing, and chunk-size warnings
  - Production HTTPS login with the provided account -> redirected to `/library`; no console errors and no `uploadProgress is not defined`
- Residual risk:
  - Whole-repo source-augmented scanner risk remains high outside this scoped prompt.
  - Dirty generated Python `__pycache__` files remain in the worktree and were intentionally not reverted or committed.

---

## Scoped AI Slop Audit - Protected PDF Rendering Boundary (2026-06-12)

**Verdict**
Score: 12/100, Minimal slop risk for the scoped protected-PDF rendering fix after repair
Confidence: Medium

**Why**
- Graphify was read first. The relevant graph targets were Community 13 (`PDFProvider`, `ReaderPage`), Community 25 (PDF.js initialization), Community 8 (`apiRequest()` and authenticated API helpers), and the deployment nginx config outside the graph.
- The required Graphify scanner still reports severe whole-repo source-augmented triage risk, but those findings are dominated by pre-existing backend hubs, local environment secret-risk hits, broad exception masking, and unrelated generated/static assets outside this prompt.
- Source and production evidence showed the user-visible "Unable to load the protected PDF" was not an ownership failure: the authenticated document metadata and `/api/files/...` request succeeded, while the PDF.js worker failed because `.mjs` was served with the wrong MIME type.
- The repair keeps security intact by preserving backend ownership checks, moving the PDF binary fetch through the authenticated API client, serving the worker as JavaScript, and deleting a stale unused PDF.js initializer that could attract future fixes into the wrong module.

**Evidence**
| Signal | Graph Evidence | Source Evidence | Classification | Likely Root Cause | Permanent Fix | Prevention Gate |
|---|---|---|---|---|---|---|
| Protected PDF rendering failed after successful auth because the PDF.js worker module was not importable | Community 25 isolates PDF.js initialization, while Community 13 owns reader rendering; the failure crossed reader and deployment boundaries. | `nginx_ssl.conf:32` now has a dedicated `.mjs` static location and `nginx_ssl.conf:35` maps `mjs` to `application/javascript`; production header validation returned `Content-Type: application/javascript`. | Confirmed slop signal, repaired | Frontend bundle output changed to `.mjs`, but nginx still used default `application/octet-stream` for that extension. | Added a scoped `.mjs` nginx location before the SPA fallback and reloaded validated nginx config. | Production deploy checks must validate module-worker MIME headers, not only that the JS bundle exists. |
| The viewer previously delegated protected PDF binary transport to React-PDF/PDF.js header plumbing | Community 8 contains the authenticated API helper hub; Community 13 contains the active reader/viewer surface. | `frontend/src/lib/api.ts:174` centralizes authenticated blob fetches; `frontend/src/lib/api.ts:188` exposes `fetchAuthenticatedBytes()`; `frontend/src/components/SimplePDFViewer.tsx:72` fetches bytes through that API client; `frontend/src/components/SimplePDFViewer.tsx:313` passes `{ data }` via `file={pdfFile}`. | Confirmed slop signal, repaired | Auth and rendering concerns were coupled inside library transport, making failures look like ownership errors and hiding the actual worker failure. | Split the boundary: app-owned authenticated fetch first, PDF.js render of already-fetched `Uint8Array` second. | Protected binary endpoints should be fetched through `apiFetch`; rendering libraries should consume validated bytes or explicit object URLs only after the app owns auth errors. |
| A stale PDF.js initializer module duplicated worker setup and pointed at the old non-module worker path | Graphify Community 25 lists `initializePDFJS()`, `loadPDFDocument()`, and `testUrlAccessibility()` as a separate PDF.js cluster, but source search found no production imports. | `frontend/src/utils/pdfJsInitializer.ts` was deleted; `frontend/tests/pdf-context-source.test.mjs:54` now guards the active `SimplePDFViewer` worker setup instead of reading the dead initializer. | Confirmed slop signal, repaired | Earlier PDF.js fallback work left an unused abstraction with stale assumptions, and the test suite kept asserting dead code. | Deleted the unused initializer and removed its source-only test, making `SimplePDFViewer` the sole active PDF.js worker owner. | Do not keep tests that preserve unused integration modules; source guards should target active runtime boundaries. |

**Aggressive Review Targets**
- `frontend/tests/pdf-context-source.test.mjs` still contains several source-inspection guards. They are useful architecture sentinels in this repo, but executable component tests would provide stronger evidence for reader behavior.
- The whole-repo scanner still reports unrelated severe triage risk around secrets, broad exception masking, backend god nodes, and generated/static PDF assets. Those are outside this protected-PDF pass.
- The Graphify snapshot is dated `2026-05-17`, so confidence remains Medium until graph output is regenerated after these repairs.

**Healthy Signals**
- The backend `/api/files/{filename}` route remains authenticated and ownership-filtered; the fix did not weaken auth for older PDFs.
- Production verification showed the target PDF rendering as `1 / 1` with extracted text visible and voiceover enabled.
- The stale PDF.js initializer is gone, so future worker/MIME fixes have one active owner.

**Workflow Gaps**
- The deploy pipeline did not validate MIME types for emitted ES module assets.
- The frontend test stack does not currently run a browser/component test that exercises React-PDF end to end.

**Highest-Risk Clusters**
- PDF rendering boundary: viewer, authenticated binary fetch, worker asset MIME, and nginx SPA fallback all need to stay aligned. The previous failure looked like auth but was actually a worker module delivery problem.

**Likely Root Causes**
- Context split between frontend rendering and deployment config: the code fix focused on auth headers before the worker asset response was inspected.
- Dead-integration residue: an unused PDF.js initializer with stale worker assumptions remained available as a false repair target.
- Missing deploy-time asset checks: production validation covered login and route health but not module-worker MIME.

**Permanent Fixes**
- Added authenticated byte fetching via `fetchAuthenticatedBytes()` and rendered PDFs from `Uint8Array` data.
- Added React-PDF load-error handling so worker/parser errors surface instead of collapsing into a generic protected-file message.
- Added nginx `.mjs` MIME handling before the SPA fallback.
- Added a worker URL cache-bust for the bad MIME migration window.
- Deleted unused `frontend/src/utils/pdfJsInitializer.ts` and removed the test that kept it alive.

**Anti-Slop Gates**
- Validate emitted worker/module asset MIME headers after production builds.
- Keep PDF.js worker ownership in one active module.
- Prefer app-owned authenticated binary fetches for protected files.
- Remove unused integration fallback modules instead of updating them speculatively.

**Validation**
- Read `graphify-out/GRAPH_REPORT.md` before raw source inspection.
- Ran required triage: `python C:/Users/SAI/.codex/skills/audit-ai-slop/scripts/graphify_slop_scan.py --graphify-out graphify-out --source-root . --format markdown`.
- Validation after repair:
  - `cd frontend && npm test` -> 17 passed
  - `cd frontend && npm run build` -> passed, with existing Browserslist, plugin timing, and chunk-size warnings
  - Production nginx header check for `pdf.worker.min-*.mjs?v=20260612-mjs` -> `Content-Type: application/javascript`
  - Production reader verification -> target PDF rendered as `1 / 1` with visible PDF text
- Residual risk:
  - Whole-repo source-augmented scanner risk remains high outside this scoped prompt.
  - Dirty generated Python `__pycache__` files remain in the worktree and were intentionally not reverted or committed.
