from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    google_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    github_token: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
