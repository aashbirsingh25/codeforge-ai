from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from app.agents.schemas import ExecutionState, ExecutionStep, AgentObservation, AgentAction
from app.planner.schemas import ExecutionPlan

class ExecutionStateManager:
    def __init__(self, plan: ExecutionPlan):
        self.state = ExecutionState(
            current_task=None,
            completed_tasks=[],
            failed_tasks=[],
            pending_tasks=[t.id for t in plan.tasks],
            observations={},
            execution_history=[],
            timestamps={},
            retry_count={}
        )
        self.state.timestamps["start_time"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def start_task(self, task_id: str) -> None:
        self.state.current_task = task_id
        if task_id in self.state.pending_tasks:
            self.state.pending_tasks.remove(task_id)
        self.state.timestamps[f"task_start_{task_id}"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        if task_id not in self.state.observations:
            self.state.observations[task_id] = []
        
        step = self.get_step(task_id)
        if not step:
            step = ExecutionStep(
                task_id=task_id,
                status="RUNNING",
                actions=[],
                observations=[],
                retry_count=self.state.retry_count.get(task_id, 0),
                start_time=self.state.timestamps[f"task_start_{task_id}"]
            )
            self.state.execution_history.append(step)
        else:
            step.status = "RUNNING"
            step.start_time = self.state.timestamps[f"task_start_{task_id}"]

    def complete_task(self, task_id: str, output: Optional[str] = None) -> None:
        self.state.current_task = None
        if task_id not in self.state.completed_tasks:
            self.state.completed_tasks.append(task_id)
        if task_id in self.state.failed_tasks:
            self.state.failed_tasks.remove(task_id)
        self.state.timestamps[f"task_end_{task_id}"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        step = self.get_step(task_id)
        if step:
            step.status = "COMPLETED"
            step.end_time = self.state.timestamps[f"task_end_{task_id}"]

    def fail_task(self, task_id: str, error: str) -> None:
        self.state.current_task = None
        if task_id not in self.state.failed_tasks:
            self.state.failed_tasks.append(task_id)
        if task_id in self.state.completed_tasks:
            self.state.completed_tasks.remove(task_id)
        self.state.timestamps[f"task_end_{task_id}"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        step = self.get_step(task_id)
        if step:
            step.status = "FAILED"
            step.error = error
            step.end_time = self.state.timestamps[f"task_end_{task_id}"]

    def record_action_and_observation(self, task_id: str, action: AgentAction, observation: AgentObservation) -> None:
        if task_id not in self.state.observations:
            self.state.observations[task_id] = []
        self.state.observations[task_id].append(observation)
        
        step = self.get_step(task_id)
        if step:
            step.actions.append(action)
            step.observations.append(observation)

    def increment_retry(self, task_id: str) -> int:
        count = self.state.retry_count.get(task_id, 0) + 1
        self.state.retry_count[task_id] = count
        step = self.get_step(task_id)
        if step:
            step.retry_count = count
        return count

    def get_step(self, task_id: str) -> Optional[ExecutionStep]:
        for step in self.state.execution_history:
            if step.task_id == task_id:
                return step
        return None

    def finalize(self) -> None:
        self.state.current_task = None
        self.state.timestamps["end_time"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
