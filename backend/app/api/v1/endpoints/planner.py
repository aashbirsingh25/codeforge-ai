from typing import List
from fastapi import APIRouter, Depends, status

from app.planner.schemas import PlanningRequest, PlanningResponse
from app.planner.service import PlannerService

router = APIRouter()


# Dependable service instantiation
def get_planner_service() -> PlannerService:
    return PlannerService()


@router.post("/plan", response_model=PlanningResponse, status_code=status.HTTP_200_OK)
async def generate_execution_plan(
    request: PlanningRequest,
    service: PlannerService = Depends(get_planner_service)
):
    """Decomposes a high-level goal into a validated, structured execution plan."""
    return await service.generate_plan(request)


@router.get("/strategies", response_model=List[str], status_code=status.HTTP_200_OK)
def list_planning_strategies(
    service: PlannerService = Depends(get_planner_service)
):
    """Lists available planning strategies that can be used to generate execution plans."""
    return service.list_strategies()
