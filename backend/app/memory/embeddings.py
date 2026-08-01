import logging
from typing import List, Optional
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger("app.memory.embeddings")


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generates a 768-dimensional text embedding using Gemini's text-embedding-004 model.
    Handles API errors gracefully by logging a warning and returning None.
    """
    if not text or not text.strip():
        return None

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.warning("Gemini API key is not configured; skipping embedding generation.")
        return None

    try:
        genai.configure(api_key=api_key)
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        if isinstance(response, dict) and "embedding" in response:
            return response["embedding"]
        elif hasattr(response, "embedding"):
            return response.embedding
        else:
            logger.warning(f"Unexpected response structure from embed_content: {response}")
            return None
    except Exception as e:
        logger.warning(f"Embedding generation failed for query/content: {e}")
        return None
