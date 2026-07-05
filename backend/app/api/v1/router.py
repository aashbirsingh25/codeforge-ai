from fastapi import APIRouter
from app.api.v1.endpoints import health, projects, agents, memory, settings

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
