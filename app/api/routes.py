from fastapi import APIRouter, HTTPException
import urllib.error
import threading
from app.models.schemas import GenerateRequest, RetrievalResult
from app.services.readme_generator import generate
from app.config import settings

router = APIRouter()
busy = threading.Lock()

@router.get('/health')
def health():
    return {'ready': bool(settings.google_api_key), 'model': settings.gemini_model}

@router.post('/generate', response_model=RetrievalResult)
def create_readme(request: GenerateRequest):
    if not busy.acquire(blocking=False):
        raise HTTPException(429, 'A README is already being generated. Please try again shortly.')
        
    try:
        result = generate(request.repo_url, request.rerank)
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
