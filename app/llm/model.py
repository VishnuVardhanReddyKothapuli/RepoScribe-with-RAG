from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings
import os

def get_llm(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=temperature,
        max_output_tokens=8192,
        google_api_key=settings.google_api_key or os.getenv("GOOGLE_API_KEY")
    )
