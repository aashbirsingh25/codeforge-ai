from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.schemas import ExecutionRequest, ExecutionResponse, ReActTrace
from app.agents.service import execution_service, AgentExecutionService
from app.planner.schemas import ExecutionPlan
from app.core.exceptions import CodeForgeException

router = APIRouter()


# Dependency provider for AgentExecutionService
def get_execution_service() -> AgentExecutionService:
    return execution_service


@router.get("")
def list_agents():
    """
    Get configured autonomous software engineering sub-agents.
    """
    return {
        "agents": [
            {
                "id": "planner",
                "name": "Planner Agent",
                "role": "Planning and task deconstruction",
                "status": "ready"
            },
            {
                "id": "coding",
                "name": "Coding Agent",
                "role": "Code generation and modifications",
                "status": "ready"
            },
            {
                "id": "reviewer",
                "name": "Reviewer Agent",
                "role": "Code review and style verification",
                "status": "ready"
            },
            {
                "id": "debugger",
                "name": "Debugger Agent",
                "role": "Error analysis and correction loops",
                "status": "ready"
            }
        ]
    }


@router.post("/execute", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_goal_or_plan(
    request: ExecutionRequest,
    service: AgentExecutionService = Depends(get_execution_service)
):
    """
    Executes a high-level goal (by automatically planning first) or executes an existing plan.
    """
    try:
        return await service.execute_request(request)
    except CodeForgeException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # CodeForgeException will be handled by the centralized handler, but here we catch general errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/execute/plan", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_existing_plan(
    plan: ExecutionPlan,
    service: AgentExecutionService = Depends(get_execution_service)
):
    """
    Executes an existing structured execution plan.
    """
    try:
        request = ExecutionRequest(plan=plan)
        return await service.execute_request(request)
    except CodeForgeException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/status", response_model=ExecutionResponse, status_code=status.HTTP_200_OK)
def get_execution_status(
    execution_id: Optional[str] = None,
    service: AgentExecutionService = Depends(get_execution_service)
):
    """
    Gets the current or latest execution status. Returns 404 if no execution exists.
    """
    response = service.get_status(execution_id)
    if not response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No execution found.")
    return response


@router.get("/history", response_model=List[ExecutionResponse], status_code=status.HTTP_200_OK)
def get_execution_history(
    service: AgentExecutionService = Depends(get_execution_service)
):
    """
    Lists historical and current execution logs.
    """
    return service.get_history()


@router.get("/{execution_id}/trace", response_model=ReActTrace, status_code=status.HTTP_200_OK)
def get_execution_trace(
    execution_id: str,
    service: AgentExecutionService = Depends(get_execution_service)
):
    """
    Retrieve the complete reasoning and tool execution trace for a specific agent execution.
    """
    response = service.get_status(execution_id)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID '{execution_id}' not found."
        )
    if not response.react_trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trace found for execution ID '{execution_id}'."
        )
    return response.react_trace

