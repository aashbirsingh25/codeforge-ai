import uuid
import logging
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.agents.schemas import ExecutionRequest, ExecutionResponse, ExecutionState, ExecutionMetrics
from app.agents.executor import AgentExecutor
from app.planner.service import PlannerService
from app.planner.schemas import PlanningRequest
from app.core.config import settings

logger = logging.getLogger("app.agents.service")

class AgentExecutionService:
    def __init__(self):
        # In-memory storage for executions: execution_id -> ExecutionResponse
        self._executions: Dict[str, ExecutionResponse] = {}
        # Track active asyncio tasks for cancel propagation
        self._active_tasks: Dict[str, asyncio.Task] = {}
        # Track active executors for cancel adjustments
        self._active_executors: Dict[str, AgentExecutor] = {}

    async def execute_request(self, request: ExecutionRequest, provider: str = "gemini", max_retries: int = 3) -> ExecutionResponse:
        execution_id = str(uuid.uuid4())
        
        # 1. Resolve Plan
        plan = request.plan
        if not plan:
            if not request.goal:
                raise ValueError("Either 'goal' or 'plan' must be provided in ExecutionRequest.")
            
            # Publish planning event
            try:
                from app.core.events import event_publisher
                event_publisher.publish(execution_id, "planning", {"goal": request.goal})
            except Exception:
                pass
                
            logger.info(f"No execution plan provided. Automatically generating plan for goal: '{request.goal}'")
            planner_service = PlannerService()
            planning_req = PlanningRequest(goal=request.goal, provider=provider)
            planning_resp = await planner_service.generate_plan(planning_req)
            plan = planning_resp.plan
        
        # 2. Run executor
        executor = AgentExecutor(plan, provider=provider, max_retries=max_retries, execution_id=execution_id)
        
        # Record start times
        start_time_iso = executor.state_mgr.state.timestamps["start_time"]
        start_time_perf = time.perf_counter()
        
        init_metrics = ExecutionMetrics(
            start_time=start_time_iso,
            end_time=None,
            duration_seconds=0.0,
            retry_count=0
        )
        init_response = ExecutionResponse(
            execution_id=execution_id,
            status="RUNNING",
            plan=plan,
            state=executor.state_mgr.state,
            metrics=init_metrics,
            react_trace=executor.react_trace
        )
        self._executions[execution_id] = init_response
        
        # Associate active task
        current_task = asyncio.current_task()
        self._active_tasks[execution_id] = current_task
        self._active_executors[execution_id] = executor
        
        try:
            response = await executor.execute()
            response.execution_id = execution_id
            self._executions[execution_id] = response
            
            # Telemetry metrics
            try:
                from app.core.metrics import metrics_tracker
                metrics_tracker.track_execution("COMPLETED", response.metrics.duration_seconds)
            except Exception:
                pass
                
            return response
            
        except asyncio.CancelledError:
            logger.info(f"Agent execution {execution_id} was cancelled.")
            executor.state_mgr.finalize()
            curr_task = executor.state_mgr.state.current_task
            if curr_task:
                executor.state_mgr.fail_task(curr_task, "Execution cancelled by user.")
                
            duration = time.perf_counter() - start_time_perf
            try:
                from app.core.metrics import metrics_tracker
                metrics_tracker.track_execution("CANCELLED", duration)
            except Exception:
                pass
                
            cancelled_metrics = ExecutionMetrics(
                start_time=start_time_iso,
                end_time=executor.state_mgr.state.timestamps.get("end_time"),
                duration_seconds=duration,
                retry_count=sum(executor.state_mgr.state.retry_count.values())
            )
            
            response = ExecutionResponse(
                execution_id=execution_id,
                status="CANCELLED",
                plan=plan,
                state=executor.state_mgr.state,
                metrics=cancelled_metrics,
                react_trace=executor.react_trace
            )
            self._executions[execution_id] = response
            
            # Save cancellation state to Memory Engine
            try:
                from app.memory.manager import MemoryManager
                MemoryManager().save_execution(
                    execution_id=execution_id,
                    goal=plan.goal,
                    status="CANCELLED",
                    tasks=plan.tasks,
                    duration=duration,
                    error="Execution cancelled by user."
                )
            except Exception as e_mem:
                logger.warning(f"Failed to log cancelled execution to memory: {e_mem}")
                
            # Publish SSE cancellation event
            try:
                from app.core.events import event_publisher
                event_publisher.publish(execution_id, "cancelled", {"execution_id": execution_id})
            except Exception:
                pass
                
            raise
            
        except Exception as e:
            executor.state_mgr.finalize()
            duration = time.perf_counter() - start_time_perf
            
            try:
                from app.core.metrics import metrics_tracker
                metrics_tracker.track_execution("FAILED", duration)
            except Exception:
                pass
            
            failed_metrics = ExecutionMetrics(
                start_time=start_time_iso,
                end_time=executor.state_mgr.state.timestamps.get("end_time"),
                duration_seconds=duration,
                retry_count=sum(executor.state_mgr.state.retry_count.values())
            )
            
            response = ExecutionResponse(
                execution_id=execution_id,
                status="FAILED",
                plan=plan,
                state=executor.state_mgr.state,
                metrics=failed_metrics,
                react_trace=executor.react_trace
            )
            self._executions[execution_id] = response
            raise
            
        finally:
            self._active_tasks.pop(execution_id, None)
            self._active_executors.pop(execution_id, None)

    def get_status(self, execution_id: Optional[str] = None) -> Optional[ExecutionResponse]:
        if not execution_id:
            if not self._executions:
                return None
            latest_id = list(self._executions.keys())[-1]
            return self._executions[latest_id]
        return self._executions.get(execution_id)

    def get_history(self) -> List[ExecutionResponse]:
        return list(self._executions.values())

    def cancel_execution(self, execution_id: str) -> bool:
        """Gracefully aborts a running execution by cancelling its asyncio task thread."""
        task = self._active_tasks.get(execution_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def cleanup_stale_executions(self, timeout_seconds: float = 3600.0) -> None:
        """Removes stale executions older than the timeout and cancels runs exceeding active limits."""
        now = datetime.now(timezone.utc)
        to_remove = []
        for exec_id, response in list(self._executions.items()):
            end_time_str = response.metrics.end_time
            if end_time_str:
                try:
                    end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                    if (now - end_time).total_seconds() > timeout_seconds:
                        to_remove.append(exec_id)
                except Exception:
                    pass
            elif response.status == "RUNNING":
                start_time_str = response.metrics.start_time
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    if (now - start_time).total_seconds() > settings.AGENT_TIMEOUT:
                        task = self._active_tasks.get(exec_id)
                        if task and not task.done():
                            task.cancel()
                except Exception:
                    pass
                    
        for exec_id in to_remove:
            del self._executions[exec_id]

# Global singleton instance
execution_service = AgentExecutionService()
