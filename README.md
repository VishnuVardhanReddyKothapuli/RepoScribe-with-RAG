# RepoScribe

Generate a README from a public GitHub repository with a simple React + TypeScript interface, a local FastAPI backend, and source-cited retrieval. The interface uses warm white, charcoal, and forest green.

## Run locally

Requires Python 3.11+ and Node.js 22.12+.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set GOOGLE_API_KEY in .env. Never commit this file.
.venv\Scripts\python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. On macOS/Linux use `.venv/bin/python`, `cp`, and `npm` instead. If `.env` already exists, edit it instead of copying over it. Restart the API after changing configuration.

`GOOGLE_API_KEY` stays on the server. `GEMINI_MODEL` defaults to `gemini-3.1-flash-lite`, which passed the live availability check. Google rejected 2.5 Flash for this account, and 3.8/3.6 Flash returned high-demand errors. The browser never receives or stores the key. The server exposes `GET /api/health` and `POST /api/generate` with `{"repo_url":"https://github.com/owner/repo","rerank":false}`. This is a local single-user app; add authentication and a bounded job queue before a shared deployment.

## Deploy to Render

The root `render.yaml` defines one Python web service. Its build installs Python dependencies and compiles React; FastAPI serves `frontend/dist` alongside `/api`. No separate static site, CORS configuration, or frontend API URL is needed. Node and npm are available in [Render's native runtimes](https://render.com/docs/native-runtimes).

1. Push this repository, including `render.yaml` and `frontend/package-lock.json`, to GitHub. Keep `.env` untracked.
2. In Render, choose **New > Blueprint** and connect the repository containing these changes.
3. Enter `GOOGLE_API_KEY` when prompted, then deploy. The Blueprint sets `GEMINI_MODEL`; change it in the service's environment settings if needed.
4. Open the service's `https://<service-name>.onrender.com` URL. Check `/api/health` for `"ready": true` (key configured, not a provider connectivity test).

For manual **Web Service** setup, choose the Python runtime and leave **Root Directory** blank:

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements.txt && npm --prefix frontend ci --include=dev && npm --prefix frontend run build` |
| Start command | `python -m uvicorn api:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health check | `/api/health` |
| Python version | `PYTHON_VERSION=3.14.6` |
| Node version | `NODE_VERSION=22.22.0` |
| Required secret | `GOOGLE_API_KEY` |
| Model | `GEMINI_MODEL=gemini-3.1-flash-lite` |

Keep one worker because generation concurrency is controlled by an in-process lock. No persistent disk or database is required. The API is currently unauthenticated: anyone who can access a public deployment can consume its configured Gemini quota. Add access control before sharing it broadly.

See [Render's Blueprint reference](https://render.com/docs/blueprint-spec) for configuration details. The configuration is ready to deploy; adding it does not create a Render service.

## Retrieval and generation

`loader.py` downloads a commit-pinned GitHub archive without checking out or executing code. It reports loaded and skipped files. `main.py` chunks each file into 3,000-character passages with 600-character overlap and preserves source paths and starting lines. A BM25 lexical retriever selects evidence for README sections. An optional lexical reranker reorders candidates by query coverage and path overlap.

The old Chroma/Groq script and Streamlit generator were separate flows. They are replaced by this shared retrieval pipeline, used by both the API and evaluations. **This is a new lexical baseline, not a measured improvement over the former vector implementation.** No embedding download or external reranking service is required. A semantic reranker can be assessed later against the same dataset.

Gemini receives only selected evidence and is instructed to treat repository content as untrusted data, omit unsupported claims, and cite sources. Output with missing or unknown citation IDs, recognizable credentials, or a blocked/truncated provider response is rejected. Generated Markdown includes commit-pinned evidence links and can be previewed or downloaded.

## Evaluation dataset and commands

- `evaluations/cases.json`: 12 manually labeled retrieval questions across Click, ItsDangerous, and Requests.
- `evaluations/pallets_click.json`, `pallets_itsdangerous.json`, `psf_requests.json`: public repository snapshots, including upstream license files, pinned revisions, file content, and scale metadata.
- `evaluations/baseline.json`: offline baseline/reranking comparison, per-case rankings, Recall@1/3/5/10, index time, and retrieval p50/p95 latency.
- `evaluations/live.json`: generated READMEs, the exact evidence used, generation latency, atomic-claim faithfulness judgments, and any provider failures. Unexecuted or failed scores are null, never fabricated.
- `evaluations/scale.json`: separate synthetic size benchmark, from 42 to 840 files, including indexing memory and retrieval latency.
- `evaluations/guardrails.json`: synthetic positive/negative faithfulness controls and prompt-injection checks, executed in live mode.
- `evaluations/RESULTS.md`: measured results and their limitations.

The sample uses `random.Random(42).sample` over four public Python/TypeScript candidate repositories and happens to select three Python repositories. This is a small convenience sample, not a representative cross-language benchmark. Snapshots make runs reproducible without requiring GitHub access. Relevance labels describe selected supporting files and are not exhaustive. Existing upstream READMEs remain retrieval inputs; they are not independent reference answers, and this run does not evaluate undocumented repositories.

```powershell
# Offline: no API key or network required
.venv\Scripts\python evaluate.py
.venv\Scripts\python evaluations/scale.py

# Live: generates one README per repo and variant, then judges each (16 calls including controls, before retries)
.venv\Scripts\python evaluate.py --live --output evaluations/live.json

# Recreate only missing snapshots; --refresh explicitly replaces pinned snapshots
.venv\Scripts\python evaluations/sample.py
```

Run commands from the repository root. Reports are saved after each repository, so completed results survive later failures. A failed live run exits nonzero and preserves errors. Source content and generated documents are sent to Google during live runs.

**Recall@K** = unique labeled relevant files represented among the top K passages / total labeled relevant files. Multiple chunks from the same file cannot increase recall. Each K is evaluated independently because reranking uses a K-dependent candidate pool. Warm-up calls are excluded; p50/p95 use five timed repetitions per query at K=5. Indexing is timed separately. Online API metrics include repository download time; snapshot evaluation does not include network download time.

**Conservative faithfulness** = supported atomic factual claims with a verified verbatim evidence quote / all judged claims, with unsupported and insufficient-evidence claims included in the denominator. The model sees the exact retrieved passages, not the whole repository or an independent reference README. Supported judgments whose evidence quotes cannot be verified are downgraded to insufficient; their original verdict and reason remain in JSON. These downgrades can reflect judge quotation errors, so a low score is not proof that every downgraded claim is false. Claim-level judgments are saved for review. The same-model LLM judge can be biased and is not human ground truth. It assesses grounding, not completeness or overall documentation quality. No lexical-overlap score is presented as faithfulness.

Measured offline macro-average Recall@5 is 58.3% for both variants. Recall@10 is 87.5% for BM25 and 70.8% for reranking. Reranking increases latency, so it stays off by default. These small-sample results justify neither enabling reranking nor claiming production-level accuracy.

## Limits and guardrails

- Public HTTPS GitHub owner/repository URLs only; arbitrary hosts, credentials, query strings, and local paths are rejected.
- Maximum compressed download: 20 MB; accepted text: 4 MB, 1,000 files, 100 KB per file. Unsupported, generated, oversized, binary, environment, credential-named, and symlink files are skipped. Archives are inspected in memory and never extracted.
- Known Google/GitHub token patterns and private-key blocks are redacted before retrieval; this is not a comprehensive secret scanner. Configuration files may be omitted by filtering.
- Retrieval context is capped at 45,000 characters. Large or poorly matched files can be omitted, so the README may be incomplete. Skipped-file counts are visible.
- Citation validation checks source IDs, not whether every claim is true. Prompt instructions reduce injection risk but do not guarantee immunity. Review generated commands and statements before publication.
- Raw HTML is disabled in preview and external images are not loaded. Links remain user-initiated.
- The API accepts one generation at a time; overlapping requests return 429. Provider errors are sanitized so keys are not echoed. Transient 429/5xx responses receive up to two bounded retries.

## Checks

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
cd frontend
npm.cmd run build
```

Tests cover URL validation, archive limits, symlinks, filters, redaction, chunk provenance, retrieval, Recall@K deduplication, citation guards, generation plumbing, judge scoring, offline evaluation, and API error/concurrency behavior. Frontend verification includes strict TypeScript compilation and manual browser checks at 320, 768, 1024, and 1440 pixels.

Provider integration follows the [Gemini generateContent API](https://ai.google.dev/api/generate-content). Frontend setup follows [Vite](https://vite.dev/guide/) and [React TypeScript](https://react.dev/learn/typescript) guidance.
