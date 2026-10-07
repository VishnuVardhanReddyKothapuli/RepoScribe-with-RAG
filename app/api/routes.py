from fastapi import APIRouter, HTTPException
import urllib.error
import threading
from app.models.schemas import GenerateRequest, RetrievalResult, RepoChatRequest, RepoChatResponse
from app.services.readme_generator import generate
from app.services.repo_chat import chat_with_repo
from app.config import settings

router = APIRouter()
busy = threading.Lock()

@router.get('/health')
def health():
    return {'ready': bool(settings.gemini_api_key), 'model': settings.gemini_model}

@router.post('/generate', response_model=RetrievalResult)
def create_readme(request: GenerateRequest):
    if not settings.gemini_api_key:
        raise HTTPException(503, 'Set GEMINI_API_KEY in the server .env file and restart the API.')
        
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

@router.post('/chat', response_model=RepoChatResponse)
def handle_chat(request: RepoChatRequest):
    if not settings.gemini_api_key:
        raise HTTPException(503, 'Set GEMINI_API_KEY in the server .env file and restart the API.')
        
    try:
        result = chat_with_repo(request)
        return result
    except Exception as e:
        raise HTTPException(500, f'Chat error: {str(e)}')
