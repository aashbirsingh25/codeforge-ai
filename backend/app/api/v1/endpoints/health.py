from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_health():
    return {
        "status": "healthy",
        "service": "CodeForge AI API",
        "version": "1.0.0"
    }
