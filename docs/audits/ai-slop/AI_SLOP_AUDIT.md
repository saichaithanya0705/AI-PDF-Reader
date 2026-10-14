# AI Slop Audit: Hosted NVIDIA Retrieval

**Scope:** The NVIDIA hosted-embedding migration and direct deployment boundary: `embedding_service.py`, `nvidia_retrieval_config.py`, `vector_store.py`, dependency manifests, CI/deploy/setup scripts, `verify_env.py`, their tests, and the now-unreferenced backend persona-classifier module.

**Method:** Read the May 17, 2026 Graphify report and ran the bundled `graphify_slop_scan.py` once. Inspected changed source and direct call sites, compared the active embedding default with NVIDIA documentation, performed authenticated provider calls without persisting the supplied key, and executed focused tests. Scanner results are triage only, not final findings; it was not rerun after the repairs.

## Verdict

Score: **18/100, Low slop risk in the audited change**

Confidence: **Medium.** Source and local tests provide high confidence in the repaired boundary. The graph predates the changed code and provider functionality remains deployment-blocked because the supplied key received an authorization failure.

## Why

- The migration removed deployable local embedding dependencies, but an optional backend `SentenceTransformer` path and setup/install sources would have made local ML packages easy to reintroduce.
- The default embedding model had been retired: an authenticated call to the former default returned HTTP 410. The current documented model uses the same native 2048-dimensional contract, so it must select a separate FAISS namespace.
- Graphify listed the backend persona classifier among a low-cohesion area, while direct call-site inspection showed the frontend owns the active classification flow and no backend route imports that module.
- The repaired boundary has one hosted configuration source, deterministic provider response validation, a model/dimension-derived index namespace, deploy-time policy checks, and a verifier that fails through its process exit status.

## Evidence

| Signal | Graph/scanner evidence | Source evidence | Classification | Root cause | Permanent fix | Prevention gate |
| --- | --- | --- | --- | --- | --- | --- |
| Local embedding runtime in a deployable RAG path | RAG is a 13-edge core node; scanner listed `rag_service.py` and vector-store code as hotspots. | Pre-fix `embedding_service.py` loaded `SentenceTransformer` then a Transformers fallback; ingestion and query paths both call the service. | Confirmed slop signal, fixed | A local development default crossed the deployment boundary. | Hosted NVIDIA API is now the only embedding provider. | Test hosted request shape and prohibit local-model imports in the embedding service. |
| Distributed NVIDIA retrieval configuration | Scanner flagged indirection/masking but did not establish this contract mismatch alone. | Pre-fix embedding, reranking, and `get_vector_store()` each parsed parts of the hosted-provider configuration. | Confirmed slop signal, fixed | One logical provider contract was represented in several modules. | `nvidia_retrieval_config.py` validates embedding and reranking profiles; FAISS derives its dimension and namespace from the embedding profile. | Cross-boundary tests prove model/dimension index naming, hosted request shapes, and reranker endpoint/model alignment. |
| Weak external-response validation | Scanner's high score is not evidence by itself; model integrations need source review. | Pre-fix code sorted response entries only; duplicate/out-of-range indexes and non-finite numbers could reach vector normalization. | Confirmed slop signal, fixed | Trusting a plausible provider response after a happy-path mock. | Require exact `0..n-1` indexes, expected dimension, numeric finite values, and fail closed. | Tests cover duplicate indexes, `NaN`, HTTP failure, and missing credentials. |
| Transient provider outage treated as one-shot failure | No graph-specific evidence. | A single `POST` previously had no retry policy. | Confirmed reliability gap, fixed | Hosted-service semantics were added without transient-error handling. | HTTPS session retries POST only for 408, 429, and 5xx conditions. | Assert retry policy and retain timeout validation. |
| Retired embedding default | No graph-specific proof; provider contracts require live verification. | `DEFAULT_EMBEDDING_MODEL` pointed to `nvidia/llama-3.2-nv-embedqa-1b-v2`; a live request returned HTTP 410. | Confirmed deployment-blocking configuration drift, fixed | Hosted model selection was treated as a static implementation detail. | Default to `nvidia/nemotron-3-embed-1b` at its documented native 2048 dimension; namespace changes with model/dimension. | Unit test default profile and require staged smoke testing after every provider-model migration. |
| Orphaned local-model classifier | Graphify's broad low-cohesion community included persona/job concepts, but its inferred edges required source confirmation. | No production backend caller imports `persona_classifier.py`; the frontend has the live `classifyIntentLocally` flow. | Confirmed dead local-model indirection, fixed | The original fallback path remained after ownership moved to the frontend. | Delete the unreferenced backend classifier instead of retaining a weaker duplicate implementation. | Direct-call-site review for model/runtime removals. |
| False-success environment verifier | Scanner broad-catch finding was triage only. | `verify_env.py` printed errors but always exited 0, so scripts could accept a failed dependency/key check. | Confirmed verification debt, fixed | Diagnostics were implemented as output rather than a process contract. | Collect failures and return nonzero; test valid and missing-key paths. | Run the verifier in deploy validation and assert exit status. |
| Local-model regression path | Scanner dependency hits were broad triage. | Requirements were cleaned, but CI/deploy/setup had no shared enforcement and the environment verifier previously imported `SentenceTransformer`. | Confirmed workflow gap, fixed | Dependency removal did not establish an ownership or prevention boundary. | One policy script scans deployable runtime imports, manifests, and install surfaces; it runs before CI and deployment installs. | Policy tests cover forbidden imports, packages, PyTorch index usage, and verifier imports. |

## Healthy Signals

- Ingestion generates passage embeddings and RAG query paths generate query embeddings through the same service boundary.
- API keys are read only from environment variables and are not embedded in source or test fixtures.
- The new FAISS namespace includes both the model and dimension, preventing accidental reuse of 384-dimensional local indexes.
- The tests assert request modes, response order, failure behavior, index namespace, and validation failures rather than only mocked method existence.
- The live NVIDIA client does not record the API key or response body; it reports a safe HTTP status for operator diagnosis.

## Aggressive Review Targets

- **Resolved:** The backend persona classifier had no production caller and duplicated frontend-owned behavior. It was removed rather than kept as a token keyword fallback.
- **Pending provider owner action:** The supplied NVIDIA key produced `403 Authorization failed` for the current model. Rotate it because it was shared in chat, create/enable a deployment-scoped key with access to the model, then run the smoke test before deployment.
- **Pending provider verification:** The hosted reranker remains a direct connected boundary but was not live-tested after the embedding call was blocked by authorization. Verify its configured model/endpoint with the replacement key before enabling a production rollout.
- The scanner found a tracked local `.env` with credential-shaped values. This audit did not alter it because it is outside the requested migration and remediation requires credential rotation; treat it as a priority security review item without copying values into logs or reports.
- The graph is dated May 17, 2026 and reports 373 isolated nodes plus low-cohesion core communities. Those are whole-repository review targets, not evidence against this focused change.

## Workflow Gaps

- A live embedding smoke test reached NVIDIA but is blocked by `403 Authorization failed` with the supplied key; this is an external credential/entitlement blocker, not a fallback condition.
- The policy gate prevents local embedding runtime regressions but does not replace a secret-scanning gate for tracked environment files.

## Permanent Fixes Applied

1. Added `backend/app/nvidia_retrieval_config.py` as the shared profile boundary for embedding and reranking models, endpoints, timeouts, and the embedding index namespace.
2. Made the embedding service hosted-only with bounded transient retries and deterministic output validation.
3. Made FAISS consume the same profile and create a model/dimension-specific index.
4. Replaced the local CrossEncoder with `backend/app/reranker_service.py`, which uses the same NVIDIA key, validates complete finite rankings, and preserves hybrid retrieval only during provider failure.
5. Removed local reranking dependencies and obsolete local-model diagnostics, then added behavior-focused tests and deployment documentation.
6. Removed the unreferenced local-model persona classifier, upgraded the retired embedding default to `nvidia/nemotron-3-embed-1b` at 2048 dimensions, and preserved separate FAISS index storage through the profile namespace.
7. Added a single hosted-only policy script used by CI, remote deployment, and Windows setup; it rejects local embedding imports, packages, and the PyTorch index before installation.
8. Changed `verify_env.py` to return a nonzero exit status on missing hosted credentials or required runtime packages and added failure-path tests.

## Anti-Slop Gates

- Run `python -m pytest backend/tests` on every embedding or vector-store change.
- Add a secret-scanning CI gate and rotate any credentials found in tracked environment files.
- Add a staging smoke test that indexes one document and queries it with a real NVIDIA key stored only in the CI/deployment secret manager.
- Require a re-index migration note whenever the embedding model or vector dimension changes.
- Require provider-model ownership and a release check whenever a hosted model is retired or replaced.

## Validation

- Initial migration validation: `python -m pytest tests/test_embedding_service.py tests/test_vector_store.py tests/test_rag_service.py` — 22 passed.
- Initial reranker validation: `python -m pytest tests` — 81 passed.
- `python backend/scripts/check_hosted_embedding_policy.py` — passed.
- `python -m compileall -q backend/app backend/scripts` — passed.
- `python -m pytest backend/tests/test_hosted_embedding_policy.py backend/tests/test_nvidia_retrieval_config.py backend/tests/test_embedding_service.py backend/tests/test_verify_env.py backend/tests/test_reranker_service.py backend/tests/test_rag_service.py backend/tests/test_vector_store.py -q` — 40 passed.
- `python -m pytest backend/tests -q` — 89 passed.
- Deployment workflow YAML parsing and `git diff --check` — passed.
- Live validation: former default returned HTTP 410; current documented model reached NVIDIA but returned `403 Authorization failed` for the supplied key. No key or provider body was persisted.

## Source References

- `backend/app/nvidia_retrieval_config.py`
- `backend/app/embedding_service.py`
- `backend/app/vector_store.py`
- `backend/scripts/check_hosted_embedding_policy.py`
- `backend/tests/test_embedding_service.py`
- `backend/tests/test_hosted_embedding_policy.py`
- `backend/tests/test_nvidia_retrieval_config.py`
- `backend/tests/test_verify_env.py`
