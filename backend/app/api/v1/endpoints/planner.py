from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.planner.schemas import PlanningRequest, PlanningResponse
from app.planner.service import PlannerService
from app.core.auth import get_current_user
from app.db.base import get_db_session
from app.db.models import User
from app.memory.store import MemoryStore
from app.memory.manager import MemoryManager

router = APIRouter()


# Dependable service instantiation
def get_planner_service() -> PlannerService:
    return PlannerService()


@router.post("/plan", response_model=PlanningResponse, status_code=status.HTTP_200_OK)
async def generate_execution_plan(
    request: PlanningRequest,
    service: PlannerService = Depends(get_planner_service),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Decomposes a high-level goal into a validated, structured execution plan."""
    memory_manager = MemoryManager(store=MemoryStore(db=db, user_id=current_user.id))
    return await service.generate_plan(request, memory_manager=memory_manager)


@router.get("/strategies", response_model=List[str], status_code=status.HTTP_200_OK)
def list_planning_strategies(
    service: PlannerService = Depends(get_planner_service)
):
    """Lists available planning strategies that can be used to generate execution plans."""
    return service.list_strategies()
