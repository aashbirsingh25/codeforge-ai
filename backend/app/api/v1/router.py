from fastapi import APIRouter, Depends
from app.core.auth import verify_api_key
from app.api.v1.endpoints import health, projects, agents, memory, settings, tools, planner, workspace, chat, metrics

api_router = APIRouter()

# Public endpoint for health checks (e.g., Render)
api_router.include_router(health.router, prefix="/health", tags=["health"])

# Protected endpoints requiring X-API-Key header
api_router.include_router(projects.router, prefix="/projects", tags=["projects"], dependencies=[Depends(verify_api_key)])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"], dependencies=[Depends(verify_api_key)])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"], dependencies=[Depends(verify_api_key)])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"], dependencies=[Depends(verify_api_key)])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"], dependencies=[Depends(verify_api_key)])
api_router.include_router(planner.router, prefix="/planner", tags=["planner"], dependencies=[Depends(verify_api_key)])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"], dependencies=[Depends(verify_api_key)])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"], dependencies=[Depends(verify_api_key)])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"], dependencies=[Depends(verify_api_key)])


