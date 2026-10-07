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

The system uses **lexical RAG using BM25**. It does not use vector or semantic search.
The RAG pipeline works as follows:
1.  **Repository Loader:** Downloads a commit-pinned GitHub archive without executing code (`app.rag.loader`). File filtering and secret redaction are applied.
2.  **Chunking:** Splits files into logical chunks (e.g. classes, functions) while preserving paths (`app.rag.splitter`).
3.  **Retriever:** Uses a deterministic BM25 lexical retriever to select relevant evidence (`app.rag.retriever`).
4.  **Parallel Agents:** Specialized analysts (Repository, Feature, Setup, Quality) process the evidence concurrently using LangGraph (`app.agents.graph`).
5.  **Coordinator:** Combines the outputs from the agents into a cohesive README.
6.  **Validation:** Ensures all generated citations map directly to retrieved evidence and checks for leaked secrets.

## Run locally

Requires Python 3.11+ and Node.js 22.12+.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set GEMINI_API_KEY in .env. Never commit this file.
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. On macOS/Linux use `.venv/bin/python` and `npm` instead.

`GEMINI_API_KEY` stays on the server. `GEMINI_MODEL` defaults to `gemini-3.1-flash-lite`. The server exposes `GET /api/health` and `POST /api/generate`.

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
3. Enter `GEMINI_API_KEY` when prompted, then deploy.

For manual **Web Service** setup:
* Build command: `pip install -r requirements.txt && npm --prefix frontend ci --include=dev && npm --prefix frontend run build`
* Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`

## Evaluation

Evaluation metrics and guardrails ensure the system's faithfulness to the original repository.

```powershell
# Offline: no API key or network required
.venv\Scripts\python evaluation/run_evaluation.py
.venv\Scripts\python evaluation/metrics.py

# Live: generates one README per repo and variant, then judges each
.venv\Scripts\python evaluation/run_evaluation.py --live --output evaluation/datasets/live.json
```

### Benchmark Summary

Evaluated on **3 commit-pinned open-source repositories** using **12 labeled retrieval queries**. This is a small evaluation/smoke benchmark.

* **BM25 Recall@10** = 87.5% on the current evaluation set.
* **Conservative Faithfulness** = 60.8%
* **Baseline Retrieval p95** = ≤ 1.83 ms

Retrieval evaluation (Recall@K) measures whether known useful files were found.
Faithfulness evaluation uses an LLM-as-a-judge to estimate if generated claims are supported by the retrieved text.
Citation validation is a strict mechanical check ensuring all generated `[Snumber]` markers correspond to retrieved evidence; citation validation does not automatically prove factual correctness.

## Limitations and Guardrails

- Public HTTPS GitHub owner/repository URLs only.
- Maximum compressed download: 20 MB; accepted text: 4 MB, 1,000 files, 100 KB per file.
- Known Google/GitHub token patterns and private-key blocks are redacted before retrieval via regex. This is not a comprehensive secret scanner.
- Retrieval context is capped at 45,000 characters. 
- Validation ensures citations match retrieved evidence, but human review of facts is always recommended.
- Single-worker API design: the backend handles one generation at a time, returning 429 when busy.
