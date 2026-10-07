from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

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

class RepositoryAnalysis(BaseModel):
    project_summary: str = Field(description="Summary of the project purpose")
    architecture: str = Field(description="Architecture and main components")
    technologies: List[str] = Field(description="Important technologies and frameworks")
    entry_points: List[str] = Field(description="Main entry points of the application")

class FeatureAnalysis(BaseModel):
    features: List[str] = Field(description="Major features of the repository")
    workflows: List[str] = Field(description="Important workflows")
    api_information: Optional[str] = Field(description="APIs provided by the repository, if any")

class SetupAnalysis(BaseModel):
    requirements: List[str] = Field(description="Installation requirements")
    environment_variables: List[str] = Field(description="Required environment variables")
    installation: str = Field(description="Installation steps")
    run_commands: List[str] = Field(description="Commands to run the project")
    deployment: Optional[str] = Field(description="Deployment information")

class QualityAnalysis(BaseModel):
    testing: str = Field(description="Testing strategy")
    implementation_notes: str = Field(description="Important implementation details")
    limitations: str = Field(description="Known limitations")

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class RepoChatRequest(BaseModel):
    repository_url: str
    message: str
    conversation: List[ChatMessage] = []

class Citation(BaseModel):
    source_id: str
    path: str
    line_start: int

class RepoChatResponse(BaseModel):
    answer: str
    related: bool
    citations: List[Citation] = []
