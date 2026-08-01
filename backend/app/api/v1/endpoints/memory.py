from typing import List, Optional
from fastapi import APIRouter, Query, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.manager import MemoryManager
from app.memory.store import MemoryStore
from app.memory.schemas import (
    MemoryEntry,
    MemorySummary,
    MemoryStatistics,
    MemorySearchResponse,
)
from app.core.auth import get_current_user
from app.db.base import get_db_session
from app.db.models import User

router = APIRouter()


def get_memory_manager(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> MemoryManager:
    store = MemoryStore(db=db, user_id=current_user.id)
    return MemoryManager(store=store)


@router.get(
    "",
    response_model=MemorySummary,
    status_code=status.HTTP_200_OK,
    summary="Get memory summary",
    description="Retrieve a summary of the stored memory entries, including total count, category breakdowns, and a list of recent entries.",
    responses={
        200: {
            "description": "Success retrieving memory summary",
            "content": {
                "application/json": {
                    "example": {
                        "total_entries": 2,
                        "category_counts": {"execution": 1, "plan": 1},
                        "recent_entries": [
                            {
                                "id": "d3b07384-d113-4c4e-9c8e-cf04523d2426",
                                "timestamp": "2026-07-06T12:00:00Z",
                                "category": "plan",
                                "title": "Plan: Test Goal",
                                "content": "Execution plan generated for goal: 'Test Goal'.",
                                "metadata": {"goal": "Test Goal"},
                                "tags": ["plan", "generation"]
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_memory_summary(manager: MemoryManager = Depends(get_memory_manager)):
    return await manager.summarize()


@router.get(
    "/list",
    response_model=List[MemoryEntry],
    status_code=status.HTTP_200_OK,
    summary="List memory entries",
    description="Retrieve a list of memory entries, optionally filtered by category and tags.",
    responses={
        200: {
            "description": "Success retrieving memory list",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "d3b07384-d113-4c4e-9c8e-cf04523d2426",
                            "timestamp": "2026-07-06T12:00:00Z",
                            "category": "plan",
                            "title": "Plan: Test Goal",
                            "content": "Execution plan generated for goal: 'Test Goal'.",
                            "metadata": {"goal": "Test Goal"},
                            "tags": ["plan", "generation"]
                        }
                    ]
                }
            }
        }
    }
)
async def list_memory_entries(
    category: Optional[str] = Query(None, description="Filter by memory category"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags (entry must have all listed tags)"),
    limit: Optional[int] = Query(None, description="Limit the number of returned entries"),
    manager: MemoryManager = Depends(get_memory_manager)
):
    if not manager.store:
        return []
    return await manager.store.list(category=category, tags=tags, limit=limit)


@router.get(
    "/search",
    response_model=MemorySearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search memory entries",
    description="Query memory entries using vector similarity search with keyword fallback.",
    responses={
        200: {
            "description": "Success searching memories",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "entry": {
                                    "id": "d3b07384-d113-4c4e-9c8e-cf04523d2426",
                                    "timestamp": "2026-07-06T12:00:00Z",
                                    "category": "plan",
                                    "title": "Plan: Test Goal",
                                    "content": "Execution plan generated for goal: 'Test Goal'.",
                                    "metadata": {"goal": "Test Goal"},
                                    "tags": ["plan", "generation"]
                                },
                                "score": 1.0
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def search_memory(
    query: str = Query(..., description="Search query string"),
    category: Optional[str] = Query(None, description="Filter search by category"),
    tags: Optional[List[str]] = Query(None, description="Filter search by tags"),
    limit: int = Query(10, description="Max number of search results to return"),
    manager: MemoryManager = Depends(get_memory_manager)
):
    if not manager.store:
        return MemorySearchResponse(results=[])
    results = await manager.store.search(query=query, category=category, tags=tags, limit=limit)
    return MemorySearchResponse(results=results)


@router.get(
    "/statistics",
    response_model=MemoryStatistics,
    status_code=status.HTTP_200_OK,
    summary="Get memory storage statistics",
    description="Retrieve storage details, including total entry counts, category counts, tag counts, storage size, and last update timestamp.",
    responses={
        200: {
            "description": "Success retrieving statistics",
            "content": {
                "application/json": {
                    "example": {
                        "total_entries": 10,
                        "category_counts": {"execution": 4, "plan": 2, "tool_output": 4},
                        "tag_counts": {"execution": 4, "success": 3, "failure": 1},
                        "storage_size_bytes": 4096,
                        "last_updated": "2026-07-06T12:00:00Z"
                    }
                }
            }
        }
    }
)
async def get_memory_statistics(manager: MemoryManager = Depends(get_memory_manager)):
    if not manager.store:
        return MemoryStatistics(total_entries=0, category_counts={}, tag_counts={}, storage_size_bytes=0, last_updated=None)
    return await manager.store.statistics()


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear all memory entries",
    description="Permanently delete all memory entries stored in PostgreSQL.",
    responses={
        204: {
            "description": "Memory successfully cleared"
        }
    }
)
async def clear_memory(manager: MemoryManager = Depends(get_memory_manager)):
    await manager.clear_history()
    return None
