from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings
import os

def get_llm(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Set GEMINI_API_KEY in the server .env file to generate READMEs.")
        
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=temperature,
        max_output_tokens=8192,
        api_key=api_key
    )
