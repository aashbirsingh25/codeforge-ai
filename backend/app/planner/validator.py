from typing import List, Dict, Set
from app.planner.schemas import ExecutionPlan
from app.planner.exceptions import PlanningValidationError


class PlanValidator:
    """Validator class to enforce topological and logical constraints on generated execution plans."""

    def validate(self, plan: ExecutionPlan) -> None:
        """Runs validation checks on the plan.

        Raises PlanningValidationError if any check fails.
        """
        # 1. Goal Validation
        if not plan.goal or not plan.goal.strip():
            raise PlanningValidationError("Execution plan goal description cannot be empty.")

        # 2. Tasks presence
        if not plan.tasks:
            raise PlanningValidationError("Execution plan must contain at least one task.")

        task_ids: Set[str] = set()

        # 3. Tasks individual validations
        for task in plan.tasks:
            # Check empty fields
            if not task.id or not task.id.strip():
                raise PlanningValidationError("Task ID cannot be empty.")
            
            if not task.title or not task.title.strip():
                raise PlanningValidationError(f"Task '{task.id}' must have a non-empty title.")
            
            if not task.priority:
                raise PlanningValidationError(f"Task '{task.id}' is missing a priority value.")
            
            if not task.status:
                raise PlanningValidationError(f"Task '{task.id}' is missing a status value.")

            # Uniqueness constraint
            if task.id in task_ids:
                raise PlanningValidationError(f"Duplicate Task ID detected: '{task.id}'")
            task_ids.add(task.id)

            # Subtask validations
            subtask_ids: Set[str] = set()
            for sub in task.subtasks:
                if not sub.id or not sub.id.strip():
                    raise PlanningValidationError(f"Empty subtask ID found in task '{task.id}'.")
                
                if not sub.title or not sub.title.strip():
                    raise PlanningValidationError(f"Subtask '{sub.id}' in task '{task.id}' must have a non-empty title.")
                
                if sub.id in subtask_ids:
                    raise PlanningValidationError(f"Duplicate subtask ID '{sub.id}' within task '{task.id}'")
                subtask_ids.add(sub.id)

        # 4. Dependency checks
        for task in plan.tasks:
            for dep in task.dependencies:
                # Target ID existence
                if dep not in task_ids:
                    raise PlanningValidationError(
                        f"Task '{task.id}' references an unknown dependency ID: '{dep}'"
                    )
                # Self-dependency constraint
                if dep == task.id:
                    raise PlanningValidationError(
                        f"Task '{task.id}' cannot list itself as a dependency."
                    )

        # 5. Cycle Detection (DFS Topological Check)
        # Construct adjacency graph (ID -> list of dependency IDs)
        graph: Dict[str, List[str]] = {task.id: task.dependencies for task in plan.tasks}
        
        # 0 = UNVISITED, 1 = VISITING, 2 = VISITED
        visit_state: Dict[str, int] = {task.id: 0 for task in plan.tasks}

        def dfs_has_cycle(node: str) -> bool:
            visit_state[node] = 1  # VISITING
            for neighbor in graph.get(node, []):
                if visit_state[neighbor] == 1:
                    # Found a back-edge (cycle)
                    return True
                elif visit_state[neighbor] == 0:
                    if dfs_has_cycle(neighbor):
                        return True
            visit_state[node] = 2  # VISITED
            return False

        for task_id in graph:
            if visit_state[task_id] == 0:
                if dfs_has_cycle(task_id):
                    raise PlanningValidationError(
                        "Plan validation failed: Circular dependencies detected among tasks."
                    )
