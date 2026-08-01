import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.memory.store import MemoryStore
from app.memory.schemas import (
    MemoryEntry, 
    MemorySummary, 
    MemoryStatistics, 
    MemorySearchResult
)

logger = logging.getLogger("app.memory.manager")


class MemoryManager:
    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store

    async def save_execution(
        self,
        execution_id: str,
        goal: str,
        status: str,
        tasks: List[Any],
        duration: float,
        error: Optional[str] = None
    ) -> MemoryEntry:
        content = f"Execution {execution_id} completed with status {status} for goal: '{goal}'. Duration: {duration:.2f}s."
        if error:
            content += f" Error: {error}"
            
        metadata = {
            "execution_id": execution_id,
            "goal": goal,
            "status": status,
            "duration_seconds": duration,
            "tasks_count": len(tasks)
        }
        if error:
            metadata["error"] = error
            
        tags = ["execution", status.lower()]
        if error:
            tags.append("failure")
        else:
            tags.append("success")

        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            category="execution",
            title=f"Execution Summary: {goal[:50]}",
            content=content,
            metadata=metadata,
            tags=tags
        )
        if self.store:
            await self.store.save(entry)
        return entry

    async def save_plan(self, goal: str, plan: Any) -> MemoryEntry:
        if hasattr(plan, "model_dump"):
            plan_dict = plan.model_dump()
        elif hasattr(plan, "dict"):
            plan_dict = plan.dict()
        else:
            plan_dict = plan
            
        content = f"Execution plan generated for goal: '{goal}'."
        metadata = {
            "goal": goal,
            "plan": plan_dict
        }
        
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            category="plan",
            title=f"Plan: {goal[:50]}",
            content=content,
            metadata=metadata,
            tags=["plan", "generation"]
        )
        if self.store:
            await self.store.save(entry)
        return entry

    async def save_tool_output(
        self,
        tool_name: str,
        args: Dict[str, Any],
        output: str,
        success: bool
    ) -> MemoryEntry:
        status_str = "succeeded" if success else "failed"
        content = f"Tool '{tool_name}' {status_str}. Args: {args}. Output: {output[:200]}"
        metadata = {
            "tool_name": tool_name,
            "args": args,
            "success": success
        }
        tags = ["tool", tool_name.lower(), status_str]
        
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            category="tool_output",
            title=f"Tool Output: {tool_name}",
            content=content,
            metadata=metadata,
            tags=tags
        )
        if self.store:
            await self.store.save(entry)
        return entry

    async def save_observation(
        self,
        task_id: str,
        content: str,
        success: bool
    ) -> MemoryEntry:
        status_str = "success" if success else "failure"
        title = f"Observation: Task {task_id}"
        metadata = {
            "task_id": task_id,
            "success": success
        }
        tags = ["observation", task_id.lower(), status_str]
        
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            category="observation",
            title=title,
            content=content,
            metadata=metadata,
            tags=tags
        )
        if self.store:
            await self.store.save(entry)
        return entry

    async def save_conversation(
        self,
        conversation_id: str,
        message: str,
        role: str
    ) -> MemoryEntry:
        title = f"Conversation Message: {role}"
        metadata = {
            "conversation_id": conversation_id,
            "role": role
        }
        tags = ["conversation", conversation_id.lower(), role.lower()]
        
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            category="conversation",
            title=title,
            content=message,
            metadata=metadata,
            tags=tags
        )
        if self.store:
            await self.store.save(entry)
        return entry

    async def retrieve_recent(self, limit: int = 5, category: Optional[str] = None) -> List[MemoryEntry]:
        if not self.store:
            return []
        return await self.store.list(category=category, limit=limit)

    async def retrieve_by_tag(self, tag: str, limit: int = 5) -> List[MemoryEntry]:
        if not self.store:
            return []
        return await self.store.list(tags=[tag], limit=limit)

    async def retrieve_by_category(self, category: str, limit: int = 5) -> List[MemoryEntry]:
        if not self.store:
            return []
        return await self.store.list(category=category, limit=limit)

    async def retrieve_similar(self, query: str, limit: int = 5, category: Optional[str] = None) -> List[MemoryEntry]:
        if not self.store:
            return []
        search_results = await self.store.search(query=query, category=category, limit=limit)
        return [res.entry for res in search_results]

    async def clear_history(self) -> None:
        if self.store:
            await self.store.clear()

    async def summarize(self) -> MemorySummary:
        if not self.store:
            return MemorySummary(
                total_entries=0,
                category_counts={},
                recent_entries=[],
                short_term_contexts_count=0,
                long_term_vector_nodes=0,
                status="ready"
            )
        entries = await self.store.list()
        category_counts = {}
        for entry in entries:
            category_counts[entry.category] = category_counts.get(entry.category, 0) + 1
            
        recent_entries = entries[:5]
        
        return MemorySummary(
            total_entries=len(entries),
            category_counts=category_counts,
            recent_entries=recent_entries,
            short_term_contexts_count=len(entries),
            long_term_vector_nodes=0,
            status="ready"
        )
