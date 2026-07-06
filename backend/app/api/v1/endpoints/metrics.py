from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from typing import Dict, Any

from app.core.metrics import metrics_tracker
from app.agents.service import execution_service

router = APIRouter()

class MetricsResponse(BaseModel):
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    active_executions: int = Field(..., description="Number of currently running executions")
    completed_executions: int = Field(..., description="Cumulative completed executions count")
    failed_executions: int = Field(..., description="Cumulative failed executions count")
    cancelled_executions: int = Field(..., description="Cumulative cancelled executions count")
    memory_usage_bytes: int = Field(..., description="Process RSS memory usage in bytes")
    request_count: int = Field(..., description="Total API requests counted since startup")
    provider_usage: Dict[str, int] = Field(..., description="Completions usage metrics per LLM provider")
    average_execution_duration_seconds: float = Field(..., description="Average time duration per run execution")

@router.get(
    "",
    response_model=MetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application telemetry metrics",
    description="Returns key system statistics, resource usage, provider statistics, and execution states details.",
    responses={
        200: {
            "description": "System telemetry statistics successfully compiled",
            "content": {
                "application/json": {
                    "example": {
                        "uptime_seconds": 3600.25,
                        "active_executions": 1,
                        "completed_executions": 15,
                        "failed_executions": 2,
                        "cancelled_executions": 1,
                        "memory_usage_bytes": 104857600,
                        "request_count": 250,
                        "provider_usage": {
                            "gemini": 22,
                            "openai": 3
                        },
                        "average_execution_duration_seconds": 4.12
                    }
                }
            }
        }
    }
)
def get_telemetry_metrics():
    active_count = len(execution_service._active_tasks)
    return metrics_tracker.get_metrics(active_count=active_count)
