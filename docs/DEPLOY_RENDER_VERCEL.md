# Render Backend + Vercel Frontend Deployment

This repository is configured for a GitHub-connected Render backend and a
GitHub-connected Vercel frontend. Deploy the backend first because the frontend
production build intentionally requires the final Render URL.

## 1. Commit and push the deployment files

Push the repository branch that Render and Vercel will track. Do not commit any
`.env` file or secret. The deployment-specific files are:

- `render.yaml`
- `backend/Dockerfile`
- `.dockerignore`
- `frontend/vercel.json`

## 2. Create the Render backend

1. In Render, choose **New > Blueprint** and select this GitHub repository.
2. Render reads `render.yaml` and builds `backend/Dockerfile` from the repo root.
3. Fill every value marked `sync: false`:
   - `CORS_ORIGINS`: initially use the expected Vercel production URL, such as
     `https://your-project.vercel.app`; replace it with the exact URL after the
     first Vercel deployment if needed.
   - `SUPABASE_URL=https://hbyrlshjrhytnyyucvfu.supabase.co`.
   - `SUPABASE_ANON_KEY` (or the project's publishable key) for JWT/JWKS access.
   - `SUPABASE_SECRET_KEY` for server-only database and Storage access. Never
     add this value to Vercel or any `VITE_` variable.
   - `SUPABASE_JWT_SECRET` only if the project still issues HS256 access tokens;
     ES256 tokens are verified from the project's JWKS endpoint.
   - `GOOGLE_API_KEY` for Gemini.
   - `NVIDIA_API_KEY` for hosted embeddings and reranking.
   - `AZURE_TTS_KEY` for podcast audio, or change the TTS provider configuration.
   - `ADOBE_CLIENT_ID` for Adobe PDF Embed.
4. Apply the Blueprint and wait for `/healthz` to report HTTP 200.

The backend is stateless for document persistence: PDF objects live in the
private Supabase Storage `documents` bucket, while metadata, chunks, and
2048-dimensional NVIDIA embeddings live in Supabase Postgres/pgvector. Render's
local filesystem is only an ephemeral processing and generated-audio workspace,
so the Blueprint intentionally has no persistent disk. Keep one instance until
background ingestion is moved to a durable job queue; scale memory if real PDF
workloads exceed the selected plan.

## 3. Create the Vercel frontend

1. Import the same GitHub repository into Vercel.
2. Set **Root Directory** to `frontend`.
3. Vercel reads `frontend/vercel.json`, runs `npm ci` and `npm run build`, and
   serves `dist` with an SPA fallback for React Router deep links.
4. Add these Production environment variables before deploying:
   - `VITE_API_URL=https://your-render-service.onrender.com`
   - `VITE_SUPABASE_URL=https://hbyrlshjrhytnyyucvfu.supabase.co`
   - `VITE_SUPABASE_ANON_KEY=<your Supabase anon key>`
   - `VITE_APP_ENV=production`
   - `VITE_AUTH_BYPASS_ENABLED=false`
5. Deploy and record the final `https://...vercel.app` or custom-domain URL.

`VITE_WS_URL` is optional; when absent, the frontend converts the HTTPS Render
URL into the corresponding WSS URL.

## 4. Close the cross-origin loop

In Render, set `CORS_ORIGINS` to the exact Vercel production/custom-domain
origin with no trailing slash. Use a comma-separated list when both URLs are
needed. Redeploy the backend after changing the value.

## 5. Verify the deployed spine

1. Open `https://your-render-service.onrender.com/healthz` and expect
   `{"status":"ok"}`.
2. Load the Vercel site and confirm the browser has no CORS or mixed-content
   errors.
3. Sign in through Supabase, upload a disposable PDF, and wait for processing.
4. Query that PDF through RAG and verify hosted NVIDIA embedding and reranking
   requests succeed in Render logs.
5. Restart or redeploy the Render service and confirm the PDF and RAG query
   still work from Supabase without a Render disk.

Generated podcast/audio files are still temporary Render artifacts. Persist
those in Supabase Storage as a separate follow-up if users must retrieve them
after a restart; document files and retrieval indexes are already persistent.

## Optional local image check

From the repository root:

```powershell
docker build --platform linux/amd64 -f backend/Dockerfile -t ai-pdf-reader-api:local .
docker run --rm -p 10000:10000 --env-file backend/.env ai-pdf-reader-api:local
```

Never pass secrets through Docker build arguments. Use runtime environment
variables locally and Render's secret manager in production.
