# RepoScribe 
https://reposcribe-28hh.onrender.com/

Generate a README from a public GitHub repository with a simple React + TypeScript interface, a local FastAPI backend, and source-cited retrieval. The interface uses warm white, charcoal, and forest green.

## Architecture

RepoScribe uses a clean Python architecture with LangChain and LangGraph for parallel agent execution. 
It follows a standard structure:
* `app/api/`: FastAPI routes
* `app/agents/`: LangGraph multi-agent architecture (Repository Analyst, Feature Analyst, Setup Analyst, Quality Analyst, and Coordinator)
* `app/rag/`: Retrieval-Augmented Generation pipeline (GitHub loading, chunking, BM25 retrieval)
* `app/services/`: Services orchestrating the core logic
* `app/llm/`: LangChain LLM initialization
* `app/models/`: Pydantic models for data validation

### RAG Pipeline

The RAG pipeline works as follows:
1.  **Repository Loader:** Downloads a commit-pinned GitHub archive without executing code (`app.rag.loader`).
2.  **Chunking:** Splits files into chunks while preserving paths (`app.rag.splitter`).
3.  **Retriever:** Uses a BM25 lexical retriever to select relevant evidence (`app.rag.retriever`).
4.  **Parallel Agents:** Specialized analysts (Repository, Feature, Setup, Quality) process the evidence concurrently using LangGraph (`app.agents.graph`).
5.  **Coordinator:** Combines the outputs from the agents into a cohesive README.
6.  **Validation:** Ensures all citations are valid and no secrets are exposed.

## Run locally

Requires Python 3.11+ and Node.js 22.12+.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set GOOGLE_API_KEY in .env. Never commit this file.
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. On macOS/Linux use `.venv/bin/python`, `cp`, and `npm` instead. If `.env` already exists, edit it instead of copying over it. Restart the API after changing configuration.

`GOOGLE_API_KEY` stays on the server. `GEMINI_MODEL` defaults to `gemini-3.1-flash-lite`. The browser never receives or stores the key. The server exposes `GET /api/health` and `POST /api/generate`.

## Multi-Agent Architecture

RepoScribe utilizes LangGraph to run multiple specialized agents in parallel to deeply understand the repository:
- **Repository Analyst:** Identifies project purpose, architecture, and main components.
- **Feature Analyst:** Identifies major features, workflows, and APIs.
- **Setup Analyst:** Determines installation steps, environment variables, and run commands.
- **Code Quality Analyst:** Identifies implementation details, testing strategies, and limitations.

These agents run concurrently to improve speed, and their outputs are passed to a **Coordinator Agent** which compiles the final README.

## Deploy to Render

The root `render.yaml` defines one Python web service. Its build installs Python dependencies and compiles React; FastAPI serves `frontend/dist` alongside `/api`. 

1. Push this repository to GitHub. Keep `.env` untracked.
2. In Render, choose **New > Blueprint** and connect the repository containing these changes.
3. Enter `GOOGLE_API_KEY` when prompted, then deploy.

For manual **Web Service** setup:
* Build command: `pip install -r requirements.txt && npm --prefix frontend ci --include=dev && npm --prefix frontend run build`
* Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`

## Evaluation

Evaluation metrics and guardrails ensure the system's faithfulness to the original repository.

```powershell
# Offline: no API key or network required
.venv\Scripts\python evaluate.py
.venv\Scripts\python evaluations/scale.py

# Live: generates one README per repo and variant, then judges each
.venv\Scripts\python evaluate.py --live --output evaluations/live.json
```

## Limitations and Guardrails

<<<<<<< HEAD
- Public HTTPS GitHub owner/repository URLs only.
- Maximum compressed download: 20 MB; accepted text: 4 MB, 1,000 files, 100 KB per file.
- Known Google/GitHub token patterns and private-key blocks are redacted before retrieval.
- Retrieval context is capped at 45,000 characters. 
- Validation ensures citations match retrieved evidence, but human review of facts is always recommended.
=======
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


## 📊 Evaluation & Performance

RepoScribe includes a reproducible evaluation suite for measuring retrieval quality, latency, scalability, generation faithfulness, and safety controls.

### Benchmark Summary

Evaluated on **3 commit-pinned open-source repositories** using **12 labeled retrieval queries**.

| Metric | Result |
|---|---:|
| Repositories Evaluated | 3 |
| Files Evaluated | 289 |
| Indexed Chunks | 861 |
| Retrieval Queries | 12 |
| **BM25 Recall@5** | **58.3%** |
| **BM25 Recall@10** | **87.5%** |
| Conservative Faithfulness | 60.8% |
| **Baseline Retrieval p95** | **≤ 1.83 ms** |
| Python Regression Tests | **14 passing** |
| Guardrail Controls | **4 / 4 passed** |

### Retrieval Quality

| Repository | Files | Chunks | Recall@5 | Recall@10 |
|---|---:|---:|---:|---:|
| `pallets/click` | 155 | 514 | 37.5% | 87.5% |
| `pallets/itsdangerous` | 42 | 67 | 87.5% | **100.0%** |
| `psf/requests` | 92 | 280 | 50.0% | 75.0% |
| **Macro Average** | **289** | **861** | **58.3%** | **87.5%** |

### Retrieval Latency

Retrieval latency is measured at `K=5` after warm-up using five repetitions per query.

| Repository | p50 | p95 |
|---|---:|---:|
| `pallets/click` | 1.61 ms | 1.83 ms |
| `pallets/itsdangerous` | 0.15 ms | 0.16 ms |
| `psf/requests` | 0.70 ms | 0.81 ms |

> Retrieval timing excludes repository downloading, indexing, and LLM generation.

### Scalability

RepoScribe was stress-tested using synthetic repository expansion to measure indexing and retrieval performance.

| Files | Chunks | Text Size | Index Time | Retrieval p50 | Retrieval p95 |
|---:|---:|---:|---:|---:|---:|
| 42 | 67 | 98 KB | 20.7 ms | 0.13 ms | 0.15 ms |
| 210 | 335 | 491 KB | 101.0 ms | 0.87 ms | 0.96 ms |
| 420 | 670 | 982 KB | 187.7 ms | 1.28 ms | 1.71 ms |
| **840** | **1,340** | **1.96 MB** | **408.5 ms** | **4.59 ms** | **7.86 ms** |

The largest stress test indexed **840 files / 1,340 chunks** with approximately **10.5 MB peak traced indexing memory**.

### Safety & Reliability

The evaluation suite also verifies:

- ✅ Citation-backed README generation
- ✅ Credential and API-key redaction before retrieval
- ✅ GitHub URL allowlisting
- ✅ Path traversal protection
- ✅ Symlink and unsafe archive filtering
- ✅ Secret/private-file filtering
- ✅ Unsupported citation rejection
- ✅ LLM provider retry handling
- ✅ Prompt-injection control testing
- ✅ Hallucinated-feature detection

All **4/4 live guardrail controls passed**, including tests for:

- supported claims
- hallucinated features
- judge prompt injection
- generation prompt injection

The Python pipeline currently passes **14 regression tests**.

### Reproduce the Evaluation

```bash
# Retrieval benchmark
python evaluate.py

# Scalability benchmark
python evaluations/scale.py

# Live generation + faithfulness + guardrail evaluation
python evaluate.py --live --output evaluations/live.json
```

Live evaluation requires a configured Gemini API key.

```env
GOOGLE_API_KEY=your_api_key_here
```

> **Note:** The benchmark is intended as a reproducible smoke evaluation rather than a large-scale academic benchmark. Faithfulness is evaluated conservatively using evidence-backed claim verification and should not be interpreted as human-labeled factual accuracy.

Detailed results are available in:

```text
evaluations/
├── RESULTS.md
├── baseline.json
├── live.json
├── scale.json
├── cases.json
└── guardrails.json
```
>>>>>>> f9aed6fcd7b788622b238f0782027e5dff19dc50
