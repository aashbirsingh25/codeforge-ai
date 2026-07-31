from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.api.v1.endpoints import (
    health,
    auth,
    projects,
    agents,
    memory,
    settings,
    tools,
    planner,
    workspace,
    chat,
    metrics
)

api_router = APIRouter()

# Public endpoints (no authentication required)
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Protected endpoints requiring valid JWT access token
api_router.include_router(projects.router, prefix="/projects", tags=["projects"], dependencies=[Depends(get_current_user)])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"], dependencies=[Depends(get_current_user)])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"], dependencies=[Depends(get_current_user)])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"], dependencies=[Depends(get_current_user)])
api_router.include_router(planner.router, prefix="/planner", tags=["planner"], dependencies=[Depends(get_current_user)])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"], dependencies=[Depends(get_current_user)])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_user)])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"], dependencies=[Depends(get_current_user)])
