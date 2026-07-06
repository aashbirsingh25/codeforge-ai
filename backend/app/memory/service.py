import logging
from typing import List, Optional

from app.memory.manager import MemoryManager
from app.memory.schemas import MemoryEntry

logger = logging.getLogger("app.memory.service")

class MemoryService:
    def __init__(self, manager: Optional[MemoryManager] = None):
        self.manager = manager or MemoryManager()

    async def get_planning_context(self, goal: str) -> str:
        """Retrieves and formats relevant previous memories for planning context."""
        try:
            # 1. Retrieve similar goals (from category="plan")
            similar_plans = self.manager.retrieve_similar(query=goal, limit=3, category="plan")
            
            # 2. Retrieve recent executions (category="execution")
            recent_executions = self.manager.retrieve_recent(limit=3, category="execution")
            
            # 3. Retrieve recent failures (using tag "failure")
            recent_failures = self.manager.retrieve_by_tag(tag="failure", limit=3)
            
            # 4. Retrieve tool outputs (category="tool_output")
            recent_tool_outputs = self.manager.retrieve_recent(limit=3, category="tool_output")
            
            context_blocks = []
            
            if similar_plans:
                context_blocks.append("--- PREVIOUS SIMILAR PLANS ---")
                for i, plan in enumerate(similar_plans, 1):
                    plan_goal = plan.metadata.get("goal", "Unknown Goal")
                    plan_tasks = plan.metadata.get("plan", {}).get("tasks", [])
                    tasks_str = "\n".join([f"  - Task {t.get('id')}: {t.get('title')} ({t.get('estimated_complexity')})" for t in plan_tasks])
                    context_blocks.append(f"Similar Plan #{i}: '{plan_goal}'\nTasks:\n{tasks_str}")
            
            if recent_executions:
                context_blocks.append("--- RECENT EXECUTIONS ---")
                for i, exec_entry in enumerate(recent_executions, 1):
                    exec_goal = exec_entry.metadata.get("goal", "Unknown Goal")
                    exec_status = exec_entry.metadata.get("status", "Unknown")
                    context_blocks.append(f"Execution #{i}: '{exec_goal}' | Status: {exec_status} | Info: {exec_entry.content}")
                    
            if recent_failures:
                context_blocks.append("--- RECENT FAILURES & ERRORS ---")
                for i, fail_entry in enumerate(recent_failures, 1):
                    context_blocks.append(f"Failure #{i} [{fail_entry.category}]: {fail_entry.title}\nDetails: {fail_entry.content}")
                    
            if recent_tool_outputs:
                context_blocks.append("--- RECENT TOOL OUTPUTS ---")
                for i, tool_entry in enumerate(recent_tool_outputs, 1):
                    tool_name = tool_entry.metadata.get("tool_name", "Unknown Tool")
                    success = tool_entry.metadata.get("success", True)
                    status_str = "Success" if success else "Failed"
                    context_blocks.append(f"Tool {tool_name} ({status_str}): {tool_entry.content}")

            if not context_blocks:
                return ""
                
            return "\n\n".join(context_blocks)
        except Exception as e:
            logger.error(f"Error generating planning context: {str(e)}")
            # Do not block planning due to memory failure
            return ""

# Global memory service instance
memory_service = MemoryService()
