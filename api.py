"""Local API. Keep credentials on the server; never execute downloaded code."""
import os
import threading
import time
import urllib.error
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from loader import load_repository, repo_name
from main import generate

load_dotenv(Path(__file__).with_name('.env'))
app = FastAPI(title='RepoScribe')
busy = threading.Lock()


class GenerateRequest(BaseModel):
    repo_url: str = Field(min_length=1, max_length=200)
    rerank: bool = False


@app.get('/api/health')
def health():
    return {'ready': bool(os.getenv('GOOGLE_API_KEY')), 'model': os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite')}


@app.post('/api/generate')
def create_readme(request: GenerateRequest):
    try:
        repo_name(request.repo_url)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    if not os.getenv('GOOGLE_API_KEY'):
        raise HTTPException(503, 'Set GOOGLE_API_KEY in the server .env file and restart the API.')
    # ponytail: one local generation at a time; use a bounded job queue for multi-user deployment.
    if not busy.acquire(blocking=False):
        raise HTTPException(429, 'A README is already being generated. Please try again shortly.')
    try:
        started = time.perf_counter()
        repository = load_repository(request.repo_url)
        loaded = time.perf_counter()
        result = generate(repository, request.rerank)
        result['metrics']['load_ms'] = round((loaded - started) * 1000, 2)
        result['metrics']['total_ms'] = round((time.perf_counter() - started) * 1000, 2)
        return result
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    except urllib.error.HTTPError as error:
        raise HTTPException(502, f'GitHub returned HTTP {error.code}. Check repository visibility or retry later.') from None
    except RuntimeError as error:
        raise HTTPException(502, str(error)) from None
    except Exception:
        raise HTTPException(502, 'Repository loading or generation failed. Please retry.') from None
    finally:
        busy.release()


# Register after API routes so the frontend cannot intercept /api requests.
frontend_dist = Path(__file__).parent / 'frontend' / 'dist'
if frontend_dist.is_dir():
    app.mount('/', StaticFiles(directory=frontend_dist, html=True), name='frontend')
