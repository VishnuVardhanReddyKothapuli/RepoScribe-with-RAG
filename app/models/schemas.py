from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class GenerateRequest(BaseModel):
    repo_url: str = Field(min_length=1, max_length=200)
    rerank: bool = False

class Chunk(BaseModel):
    id: str
    path: str
    line: int
    text: str
    score: Optional[float] = None

class RetrievalResult(BaseModel):
    readme: str
    evidence: List[Dict[str, Any]]
    revision: str
    metrics: Dict[str, Any]
    grounding: str
