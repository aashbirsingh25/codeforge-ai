import uuid
import logging
from typing import Dict, List, Optional
from app.agents.schemas import ExecutionRequest, ExecutionResponse, ExecutionState
from app.agents.executor import AgentExecutor
from app.planner.service import PlannerService
from app.planner.schemas import PlanningRequest

logger = logging.getLogger("app.agents.service")

class AgentExecutionService:
    def __init__(self):
        # In-memory storage for executions: execution_id -> ExecutionResponse
        self._executions: Dict[str, ExecutionResponse] = {}

    async def execute_request(self, request: ExecutionRequest, provider: str = "gemini", max_retries: int = 3) -> ExecutionResponse:
        execution_id = str(uuid.uuid4())
        
        # 1. Resolve Plan
        plan = request.plan
        if not plan:
            if not request.goal:
                raise ValueError("Either 'goal' or 'plan' must be provided in ExecutionRequest.")
            logger.info(f"No execution plan provided. Automatically generating plan for goal: '{request.goal}'")
            planner_service = PlannerService()
            planning_req = PlanningRequest(goal=request.goal, provider=provider)
            planning_resp = await planner_service.generate_plan(planning_req)
            plan = planning_resp.plan
        
        # 2. Run executor
        executor = AgentExecutor(plan, provider=provider, max_retries=max_retries)
        
        # Initialize an initial response
        import time
        from datetime import datetime, timezone
        from app.agents.schemas import ExecutionMetrics
        
        start_time_iso = executor.state_mgr.state.timestamps["start_time"]
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
            metrics=init_metrics
        )
        self._executions[execution_id] = init_response
        
        try:
            response = await executor.execute()
            response.execution_id = execution_id
            self._executions[execution_id] = response
            return response
        except Exception as e:
            # Update response with FAILED status and error details in state
            executor.state_mgr.finalize()
            end_time_perf = time.perf_counter()
            duration = 0.0 # simple fallback or duration calculation
            
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
                metrics=failed_metrics
            )
            self._executions[execution_id] = response
            raise

    def get_status(self, execution_id: Optional[str] = None) -> Optional[ExecutionResponse]:
        if not execution_id:
            if not self._executions:
                return None
            latest_id = list(self._executions.keys())[-1]
            return self._executions[latest_id]
        return self._executions.get(execution_id)

    def get_history(self) -> List[ExecutionResponse]:
        return list(self._executions.values())


# Global singleton instance
execution_service = AgentExecutionService()
