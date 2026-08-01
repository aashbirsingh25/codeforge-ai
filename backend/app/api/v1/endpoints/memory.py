from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Query, status, Depends
from app.memory.manager import MemoryManager
from app.memory.store import MemoryStore
from app.memory.schemas import (
    MemoryEntry,
    MemorySummary,
    MemoryStatistics,
    MemorySearchResponse,
)
from app.core.config import settings
from app.core.auth import get_current_user
from app.db.models import User

router = APIRouter()

def get_memory_manager(current_user: User = Depends(get_current_user)) -> MemoryManager:
    user_memory_dir = (Path(settings.WORKSPACE_DIR).resolve() / "users" / str(current_user.id) / ".memory").resolve()
    user_memory_dir.mkdir(parents=True, exist_ok=True)
    store = MemoryStore(memory_dir=user_memory_dir)
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
def get_memory_summary(manager: MemoryManager = Depends(get_memory_manager)):
    return manager.summarize()

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
def list_memory_entries(
    category: Optional[str] = Query(None, description="Filter by memory category"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags (entry must have all listed tags)"),
    limit: Optional[int] = Query(None, description="Limit the number of returned entries"),
    manager: MemoryManager = Depends(get_memory_manager)
):
    return manager.store.list(category=category, tags=tags, limit=limit)

@router.get(
    "/search",
    response_model=MemorySearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search memory entries",
    description="Query memory entries using keyword matching, returning ranked results based on similarity scoring.",
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
                                "score": 3.0
                            }
                        ]
                    }
                }
            }
        }
    }
)
def search_memory(
    query: str = Query(..., description="Search query string"),
    category: Optional[str] = Query(None, description="Filter search by category"),
    tags: Optional[List[str]] = Query(None, description="Filter search by tags"),
    limit: int = Query(10, description="Max number of search results to return"),
    manager: MemoryManager = Depends(get_memory_manager)
):
    results = manager.store.search(query=query, category=category, tags=tags, limit=limit)
    return MemorySearchResponse(results=results)

@router.get(
    "/statistics",
    response_model=MemoryStatistics,
    status_code=status.HTTP_200_OK,
    summary="Get memory storage statistics",
    description="Retrieve storage details, including total entry counts, category counts, tag counts, storage size on disk, and last update timestamp.",
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
def get_memory_statistics(manager: MemoryManager = Depends(get_memory_manager)):
    return manager.store.statistics()

@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear all memory entries",
    description="Permanently delete all memory entries stored on disk.",
    responses={
        204: {
            "description": "Memory successfully cleared"
        }
    }
)
def clear_memory(manager: MemoryManager = Depends(get_memory_manager)):
    manager.clear_history()
    return None
