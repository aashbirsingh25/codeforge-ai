from fastapi import APIRouter
from app.api.v1.endpoints import health, projects, agents, memory, settings, tools, planner, workspace, chat, metrics

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(planner.router, prefix="/planner", tags=["planner"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])


