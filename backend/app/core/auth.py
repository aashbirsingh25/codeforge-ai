from typing import Optional
from fastapi import Header, HTTPException, status
from app.core.config import settings

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """FastAPI dependency to verify incoming X-API-Key request header against settings.API_SECRET_KEY."""
    if not x_api_key or x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return x_api_key
