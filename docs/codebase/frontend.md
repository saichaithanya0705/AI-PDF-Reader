# Frontend Documentation

## Overview

The frontend is a Vite + React + TypeScript SPA that provides:

- public landing and auth screens
- an authenticated document library
- a full reader workspace for PDF viewing, insights, chat, and podcast playback

The route tree is small, but substantial behavior is concentrated in `HomePage`, `ReaderPage`, `AuthContext`, and `PDFContext`.

## Boot And Routing

### App shell

| File | Role |
| --- | --- |
| `frontend/src/main.tsx` | mounts the React app |
| `frontend/src/App.tsx` | composes `ErrorBoundary`, `AuthProvider`, `PDFProvider`, and `BrowserRouter` |
| `frontend/src/components/ProtectedRoute.tsx` | redirects unauthenticated users to `/login` |
| `frontend/src/components/ErrorBoundary.tsx` | catches top-level render errors |

### Route map

| Route | Screen | File |
| --- | --- | --- |
| `/` | landing page | `frontend/src/pages/LandingPage.tsx` |
| `/login` | sign-in form | `frontend/src/pages/LoginPage.tsx` |
| `/signup` | registration form | `frontend/src/pages/SignupPage.tsx` |
| `/library` | authenticated document library | `frontend/src/pages/HomePage.tsx` |
| `/reader/:pdfId` | authenticated PDF reader workspace | `frontend/src/pages/ReaderPage.tsx` |

## State Model

### Authentication state

`frontend/src/context/AuthContext.tsx` is the auth source of truth. It:

- binds to Supabase auth state in normal mode
- exposes `user`, `session`, `loading`, `signIn`, `signUp`, and `signOut`
- supports a deterministic development account through `frontend/src/lib/devAuth.ts`

### PDF and document state

`frontend/src/context/PDFContext.tsx` is the document-state hub. It:

- caches documents in `localStorage`
- normalizes backend responses into a single `PDFDocument` shape
- tracks the current document, related sections, recommendations, insights, and loading flags
- performs upload, fetch, rename, delete, recommendation, and insight calls
- contains the local `classifyIntentLocally(...)` path used by the persona/job form

Helper hooks `frontend/src/context/useAuth.ts` and `frontend/src/context/usePDF.ts` simply expose those contexts safely.

## Page Responsibilities

### `LandingPage.tsx`

- product/marketing shell
- feature highlights, workflow explanation, and CTA copy
- no persistent application state

### `LoginPage.tsx`

- email/password login form
- redirect-to-origin handling after auth
- links back to landing and signup

### `SignupPage.tsx`

- registration form
- stores extra metadata such as persona/role details
- redirects toward the login flow after successful registration

### `HomePage.tsx`

This is the operational center of the frontend. It owns:

- initial document fetch and refresh
- single-file and multi-file upload flows
- local `clientId` generation and reuse
- WebSocket connection to `/ws/{clientId}`
- persona/job setup before bulk upload
- select mode, merge, split, rename, delete, and open actions
- library-level chat entry points
- sorting and status messaging

### `ReaderPage.tsx`

This is the reading workspace. It owns:

- current document resolution from route params and shared state
- page navigation synced to the URL
- sidebar and insights/podcast panel orchestration
- chat visibility and reader-side detail toggles
- reader-layout adaptation based on screen size

## Component Inventory

### Library and onboarding components

| File | Role |
| --- | --- |
| `frontend/src/components/UploadZone.tsx` | drag/drop PDF selection and validation feedback |
| `frontend/src/components/DocumentCard.tsx` | document card with open, rename, split, delete, and select behaviors |
| `frontend/src/components/AIPersonaJobForm.tsx` | persona/job UI that relies on local intent classification |
| `frontend/src/components/ChatHistory.tsx` | chat-session chooser for the library chatbot |
| `frontend/src/components/SimpleChatbot.tsx` | library-level chat UI and history interaction |

### Reader workspace components

| File | Role |
| --- | --- |
| `frontend/src/components/SmartPDFViewer.tsx` | thin wrapper around the active viewer |
| `frontend/src/components/SimplePDFViewer.tsx` | main PDF viewing surface, selection handling, and audio actions |
| `frontend/src/components/RelatedDocumentsSidebar.tsx` | related-document and cross-doc navigation surface |
| `frontend/src/components/FloatingInsightsPanel.tsx` | floating insight display |
| `frontend/src/components/InsightsNotification.tsx` | transient insight/status prompt |
| `frontend/src/components/PodcastModal.tsx` | podcast generation and playback modal |

### Alternate or lightly wired components

The following files are present and appear to be secondary, legacy, or only partially wired into the current route tree:

| File | Current status |
| --- | --- |
| `frontend/src/components/TextSelectionTooltip.tsx` | alternate text-selection UI path |
| `frontend/src/components/CrossDocumentHighlights.tsx` | auxiliary highlight surface |
| `frontend/src/components/RecommendationsPanel.tsx` | recommendations UI not obviously on the current route path |
| `frontend/src/components/InsightsPanel.tsx` | alternate insights panel |
| `frontend/src/components/PersonaJobForm.tsx` | older persona/job form |

## API And Backend Integration

### API client layer

| File | Role |
| --- | --- |
| `frontend/src/lib/api.ts` | authenticated fetch wrapper, JSON parsing, auth failure handling, blob download helper |
| `frontend/src/lib/supabaseClient.ts` | Supabase browser client or guarded stub when env vars are absent |
| `frontend/src/config.ts` | resolves `API_URL` and `WS_URL` from env vars or heuristics |

### Major backend interactions

The frontend calls these backend capabilities directly:

- `/api/documents` and `/api/documents/:id`
- `/upload/active_file` and `/upload/context_files`
- `/api/recommendations/:id`
- `/api/insights/:id`
- `/api/chat`
- `/api/text-selection-analysis`
- `/api/ask-gpt`
- `/api/generate-podcast`
- `/api/split-document`
- `/api/merge-documents`
- `/ws/{clientId}` for progress updates

## PDF Rendering And Browser Utilities

### Active PDF path

`SimplePDFViewer.tsx` is the current PDF engine. It:

- uses `react-pdf`
- configures `pdfjs` with a local worker bundle
- fetches protected PDFs through authenticated blob URLs
- manages page navigation, zoom, selection UI, and audio actions

### Supporting utility files

| File | Role |
| --- | --- |
| `frontend/src/utils/pdfValidator.ts` | client-side PDF validation before upload |
| `frontend/src/utils/pdfJsInitializer.ts` | local-only PDF.js bootstrap helper, apparently not the primary active path today |
| `frontend/src/utils/networkDetection.ts` | online/offline and Adobe API availability helpers, appears dormant in the current route tree |

### Static PDF assets

The `frontend/public/` worker and bundle files support PDF.js fallback or local delivery:

- `pdf.worker.mjs`
- `pdf.worker.min.js`
- `pdf.min.js`
- `pdf-worker-fallback.js`

## Styling, Build, And Tests

### Tooling and style files

| File | Role |
| --- | --- |
| `frontend/package.json` | scripts and dependency manifest |
| `frontend/package-lock.json` | locked dependency graph |
| `frontend/vite.config.ts` | Vite configuration |
| `frontend/eslint.config.js` | ESLint configuration |
| `frontend/tailwind.config.js` | Tailwind theme extensions |
| `frontend/postcss.config.js` | PostCSS configuration |
| `frontend/src/index.css` | global styles and font imports |
| `frontend/index.html` | Vite HTML shell |

### Tests

The frontend test surface is currently small:

| File | Focus |
| --- | --- |
| `frontend/tests/pdf-context-source.test.mjs` | source-shape guard that checks `PDFContext` and local PDF.js assumptions |

## Environment Model

- `frontend/.env.example` is written like a deployment example.
- `frontend/.env.local.example` is written like a local-development example.
- Browser-visible values must begin with `VITE_`.
- Auth bypass only applies in development conditions and pairs with backend dev-bypass behavior.

## Known Inconsistencies And Risks

- `frontend/src/config.ts` falls back to `http://localhost:8000`, while README and env examples document backend port `8080`.
- The repo documents multiple frontend env target filenames for local and deployment usage rather than a single canonical destination file.
- `HomePage.tsx` references `uploadProgress` even though the current code path does not obviously define matching state in the component.
- Several alternate components and utilities remain in the tree without a clearly active route path.

## Frontend Maintenance Guidance

- Treat `PDFContext.tsx` as the behavioral hub for document state and backend response normalization.
- Keep auth concerns in `AuthContext.tsx`, `supabaseClient.ts`, and `devAuth.ts`.
- Avoid growing more orchestration inside `App.tsx`; route-level complexity belongs in pages and context providers.
- Before removing “unused” viewer or insights components, verify whether any dormant navigation or manual QA flow still depends on them.
