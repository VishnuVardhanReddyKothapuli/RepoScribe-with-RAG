from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.1-flash-lite"
    github_token: Optional[str] = None
    
    # RAG parameters
    top_k_retrieval: int = 4
    max_evidence_chars: int = 45000
    chunk_size: int = 3000
    chunk_overlap: int = 600
    
    # Loader limits
    max_archive_bytes: int = 20_000_000
    max_total_bytes: int = 4_000_000
    max_file_bytes: int = 100_000
    max_files: int = 1000

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
