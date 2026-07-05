from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("")
def get_settings():
    """
    Get backend operational configurations.
    """
    return {
        "project_name": settings.PROJECT_NAME,
        "api_v1_str": settings.API_V1_STR,
        "workspace_dir": str(settings.WORKSPACE_DIR)
    }

@router.post("")
def update_settings():
    """
    Update configuration options (placeholder).
    """
    return {"status": "configuration updated (placeholder)"}

import os
from typing import List
from app.llm import ProviderFactory, ProviderInfo, ProviderHealthResponse

@router.get("/providers", response_model=List[ProviderInfo])
def get_providers_info():
    """
    Returns configured providers and their available models.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    from app.llm.providers.gemini import GeminiProvider
    from app.llm.providers.openai import OpenAIProvider
    
    return [
        ProviderInfo(
            name="gemini",
            available_models=GeminiProvider.SUPPORTED_MODELS,
            is_configured=bool(gemini_key)
        ),
        ProviderInfo(
            name="openai",
            available_models=OpenAIProvider.SUPPORTED_MODELS,
            is_configured=bool(openai_key)
        )
    ]

@router.get("/providers/health", response_model=List[ProviderHealthResponse])
async def check_providers_health():
    """
    Performs real-time validation checks for configured providers.
    """
    results = []
    
    # Check Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            prov = ProviderFactory.get_provider("gemini")
            healthy = await prov.health_check()
            results.append(
                ProviderHealthResponse(
                    provider="gemini",
                    status="healthy" if healthy else "unhealthy"
                )
            )
        except Exception as e:
            results.append(
                ProviderHealthResponse(
                    provider="gemini",
                    status="unhealthy",
                    error_message=str(e)
                )
            )
    else:
        results.append(
            ProviderHealthResponse(
                provider="gemini",
                status="unhealthy",
                error_message="Gemini API Key is not set in environment."
            )
        )
        
    # Check OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            prov = ProviderFactory.get_provider("openai")
            healthy = await prov.health_check()
            results.append(
                ProviderHealthResponse(
                    provider="openai",
                    status="healthy" if healthy else "unhealthy"
                )
            )
        except Exception as e:
            results.append(
                ProviderHealthResponse(
                    provider="openai",
                    status="unhealthy",
                    error_message=str(e)
                )
            )
    else:
        results.append(
            ProviderHealthResponse(
                provider="openai",
                status="unhealthy",
                error_message="OpenAI API Key is not set in environment."
            )
        )
        
    return results
