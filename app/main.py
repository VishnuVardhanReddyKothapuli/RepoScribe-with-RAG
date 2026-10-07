from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api.routes import router

app = FastAPI(title='RepoScribe')

app.include_router(router, prefix="/api")

# Register after API routes so the frontend cannot intercept /api requests.
frontend_dist = Path(__file__).parent.parent / 'frontend' / 'dist'
if frontend_dist.is_dir():
    app.mount('/', StaticFiles(directory=frontend_dist, html=True), name='frontend')
