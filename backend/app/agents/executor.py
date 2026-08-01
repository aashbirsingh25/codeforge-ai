import logging
import time
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from collections import deque

from app.planner.schemas import ExecutionPlan, Task
from app.agents.schemas import (
    ExecutionResponse,
    ExecutionMetrics,
    AgentResult,
    AgentAction,
    AgentObservation,
    ReActTrace,
    ReActStep
)
from app.agents.state import ExecutionStateManager
from app.agents.registry import agent_registry
from app.agents.exceptions import (
    AgentExecutionError,
    AgentDependencyError,
    AgentToolError,
    AgentRetryExceededError
)
from app.llm.exceptions import LLMException
from app.memory.manager import MemoryManager

logger = logging.getLogger("app.agents.executor")


def topological_sort(tasks: List[Task]) -> List[Task]:
    """Arranges tasks based on dependency graph, checking for cycles and missing tasks."""
    task_map = {t.id: t for t in tasks}
    adj = {t.id: [] for t in tasks}
    in_degree = {t.id: 0 for t in tasks}
    
    for t in tasks:
        for dep in t.dependencies:
            if dep in task_map:
                adj[dep].append(t.id)
                in_degree[t.id] += 1
            else:
                raise AgentDependencyError(f"Task '{t.id}' depends on missing task '{dep}'.")

    queue = deque([t.id for t in tasks if in_degree[t.id] == 0])
    sorted_ids = []
    
    while queue:
        u = queue.popleft()
        sorted_ids.append(u)
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                
    if len(sorted_ids) != len(tasks):
        raise AgentDependencyError("Circular dependency detected in execution plan.")
        
    return [task_map[tid] for tid in sorted_ids]


class AgentExecutor:
    def __init__(
        self,
        plan: ExecutionPlan,
        provider: str = "gemini",
        max_retries: int = 3,
        execution_id: Optional[str] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        self.plan = plan
        self.provider = provider
        self.max_retries = max_retries
        self.state_mgr = ExecutionStateManager(plan)
        self.execution_id = execution_id or str(uuid.uuid4())
        self.react_trace = ReActTrace(execution_id=self.execution_id, steps=[])
        self.memory_manager = memory_manager
        self._pending_memory_tasks: List[asyncio.Task] = []
        self._memory_lock = asyncio.Lock()

    async def _flush_pending_memory_tasks(self) -> None:
        """Awaits all pending background memory save tasks and logs any exceptions."""
        if self._pending_memory_tasks:
            results = await asyncio.gather(*self._pending_memory_tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.warning(f"Pending memory save task failed: {res}")
            self._pending_memory_tasks.clear()

    async def execute(self) -> ExecutionResponse:
        start_time_perf = time.perf_counter()
        start_time_iso = self.state_mgr.state.timestamps["start_time"]
        
        # Publish started event
        try:
            from app.core.events import event_publisher
            event_publisher.publish(self.execution_id, "started", {"execution_id": self.execution_id})
        except Exception:
            pass
            
        try:
            try:
                ordered_tasks = topological_sort(self.plan.tasks)
                # Publish planning event
                try:
                    from app.core.events import event_publisher
                    event_publisher.publish(
                        self.execution_id,
                        "planning",
                        {"goal": self.plan.goal, "tasks_count": len(self.plan.tasks)}
                    )
                except Exception:
                    pass
            except AgentDependencyError as e:
                self.state_mgr.finalize()
                end_time_perf = time.perf_counter()
                duration = end_time_perf - start_time_perf
                metrics = ExecutionMetrics(
                    start_time=start_time_iso,
                    end_time=self.state_mgr.state.timestamps["end_time"],
                    duration_seconds=duration,
                    retry_count=0
                )
                # Publish failed event
                try:
                    from app.core.events import event_publisher
                    event_publisher.publish(self.execution_id, "failed", {"execution_id": self.execution_id, "error": str(e)})
                except Exception:
                    pass
                # Save execution summary for dependency error
                if self.memory_manager:
                    try:
                        async with self._memory_lock:
                            await self.memory_manager.save_execution(
                                execution_id=self.execution_id,
                                goal=self.plan.goal,
                                status="FAILED",
                                tasks=self.plan.tasks,
                                duration=duration,
                                error=str(e)
                            )
                    except Exception as ex_mem:
                        logger.warning(f"Failed to save execution summary to memory on dependency error: {ex_mem}")
                raise

            logger.info(f"Starting execution of plan. Goal: '{self.plan.goal}'. Task order: {[t.id for t in ordered_tasks]}")

            for task in ordered_tasks:
                # Skip completed tasks
                if task.id in self.state_mgr.state.completed_tasks:
                    logger.info(f"skipping completed task: task_id={task.id}")
                    continue

                # Skip failed tasks
                if task.id in self.state_mgr.state.failed_tasks:
                    logger.info(f"skipping failed task: task_id={task.id}")
                    continue

                # Detect failed dependencies
                failed_deps = [dep for dep in task.dependencies if dep in self.state_mgr.state.failed_tasks]
                if failed_deps:
                    error_msg = f"Task '{task.id}' cannot be executed due to failed dependencies: {failed_deps}."
                    logger.error(f"task failed: task_id={task.id} error={error_msg}")
                    self.state_mgr.fail_task(task.id, error_msg)
                    self.state_mgr.finalize()
                    # Publish failed event
                    try:
                        from app.core.events import event_publisher
                        event_publisher.publish(self.execution_id, "failed", {"execution_id": self.execution_id, "error": error_msg})
                    except Exception:
                        pass
                    raise AgentDependencyError(error_msg)

                # Start task execution
                self.state_mgr.start_task(task.id)
                logger.info(f"task started: task_id={task.id}")

                success = False
                task_error_details = ""
                
                while not success:
                    current_retry = self.state_mgr.state.retry_count.get(task.id, 0)
                    
                    try:
                        agent = agent_registry.get_agent("ExecutorAgent")
                        
                        def record_action_callback(action: AgentAction, observation: AgentObservation):
                            self.state_mgr.record_action_and_observation(task.id, action, observation)
                            logger.info(
                                f"tool invoked: tool_name={action.tool_name} success={observation.success}"
                            )
                            logger.info(
                                f"tool output: content={observation.content if observation.success else observation.error}"
                            )
                            
                            # Structured Logging
                            try:
                                from app.core.logging import log_structured_event
                                log_structured_event(
                                    event="tool_call",
                                    execution_id=self.execution_id,
                                    provider=self.provider,
                                    tool=action.tool_name,
                                    status="success" if observation.success else "failed"
                                )
                            except Exception:
                                pass

                            # Emit tool events
                            try:
                                from app.core.events import event_publisher
                                event_publisher.publish(
                                    self.execution_id,
                                    "tool_call",
                                    {
                                        "task_id": task.id,
                                        "tool_name": action.tool_name,
                                        "tool_args": action.tool_args
                                    }
                                )
                                event_publisher.publish(
                                    self.execution_id,
                                    "tool_result",
                                    {
                                        "task_id": task.id,
                                        "tool_name": action.tool_name,
                                        "success": observation.success,
                                        "output": observation.content or "",
                                        "error": observation.error
                                    }
                                )
                                obs_content = observation.content if observation.success else (observation.error or "Unknown error")
                                event_publisher.publish(
                                    self.execution_id,
                                    "observation",
                                    {
                                        "task_id": task.id,
                                        "content": obs_content,
                                        "success": observation.success
                                    }
                                )
                            except Exception:
                                pass

                            if self.memory_manager:
                                obs_content = observation.content if observation.success else (observation.error or "Unknown error")
                                async def _save_action_memories():
                                    try:
                                        async with self._memory_lock:
                                            await self.memory_manager.save_tool_output(
                                                tool_name=action.tool_name,
                                                args=action.tool_args,
                                                output=observation.content or "",
                                                success=observation.success
                                            )
                                            await self.memory_manager.save_observation(
                                                task_id=task.id,
                                                content=obs_content,
                                                success=observation.success
                                            )
                                    except Exception as e_mem:
                                        logger.warning(f"Failed to save tool callback to memory: {e_mem}")

                                task_obj = asyncio.create_task(_save_action_memories())
                                self._pending_memory_tasks.append(task_obj)

                        def record_react_step_callback(step: ReActStep):
                            self.react_trace.steps.append(step)
                            
                            # Structured Logging
                            try:
                                from app.core.logging import log_structured_event
                                log_structured_event(
                                    event="thinking",
                                    execution_id=self.execution_id,
                                    provider=self.provider,
                                    status="success"
                                )
                            except Exception:
                                pass

                            # Emit thinking event
                            try:
                                from app.core.events import event_publisher
                                event_publisher.publish(
                                    self.execution_id,
                                    "thinking",
                                    {
                                        "task_id": task.id,
                                        "thought": step.thought.reasoning if step.thought else ""
                                    }
                                )
                            except Exception:
                                pass

                            if self.memory_manager and step.thought and step.thought.reasoning:
                                async def _save_step_memory():
                                    try:
                                        async with self._memory_lock:
                                            await self.memory_manager.save_observation(
                                                task_id=task.id,
                                                content=f"Thought reasoning: {step.thought.reasoning}",
                                                success=True
                                            )
                                    except Exception as e_mem:
                                        logger.warning(f"Failed to record react step to memory: {e_mem}")

                                task_obj = asyncio.create_task(_save_step_memory())
                                self._pending_memory_tasks.append(task_obj)

                        context = {
                            "task": task,
                            "provider": self.provider,
                            "action_recorder": record_action_callback,
                            "react_trace_callback": record_react_step_callback
                        }
                        
                        result = await agent.execute(task.id, context)
                        
                        if result.success:
                            self.state_mgr.complete_task(task.id, result.output)
                            logger.info(f"task completed: task_id={task.id}")
                            success = True
                        else:
                            raise AgentExecutionError(result.error or "Agent returned failure.")

                    except LLMException as ex:
                        logger.error(f"task failed due to provider error: task_id={task.id} error={ex}")
                        self.state_mgr.fail_task(task.id, str(ex))
                        self.state_mgr.finalize()
                        if self.memory_manager:
                            try:
                                async with self._memory_lock:
                                    await self.memory_manager.save_observation(task_id=task.id, content=f"LLM Error: {str(ex)}", success=False)
                            except Exception:
                                pass
                        raise
                    except asyncio.CancelledError:
                        raise
                    except Exception as ex:
                        task_error_details = str(ex)
                        if self.memory_manager:
                            try:
                                async with self._memory_lock:
                                    await self.memory_manager.save_observation(
                                        task_id=task.id,
                                        content=f"Error on retry {current_retry}: {str(ex)}",
                                        success=False
                                    )
                            except Exception:
                                pass
                        
                        if current_retry < self.max_retries:
                            count = self.state_mgr.increment_retry(task.id)
                            logger.info(f"retry attempt: task_id={task.id} retry_count={count}")
                        else:
                            logger.error(f"task failed: task_id={task.id} error={task_error_details}")
                            self.state_mgr.fail_task(task.id, f"Retry limit exceeded. Last error: {task_error_details}")
                            self.state_mgr.finalize()
                            raise AgentRetryExceededError(
                                f"Task '{task.id}' failed after {self.max_retries} retries. Last error: {task_error_details}"
                            ) from ex

            self.state_mgr.finalize()
            end_time_perf = time.perf_counter()
            duration = end_time_perf - start_time_perf
            
            logger.info(f"execution duration: {duration:.4f}s")
            total_retries = sum(self.state_mgr.state.retry_count.values())
            
            metrics = ExecutionMetrics(
                start_time=start_time_iso,
                end_time=self.state_mgr.state.timestamps["end_time"],
                duration_seconds=duration,
                retry_count=total_retries
            )

            status = "COMPLETED" if not self.state_mgr.state.failed_tasks else "FAILED"
            response = ExecutionResponse(
                execution_id=self.execution_id,
                status=status,
                plan=self.plan,
                state=self.state_mgr.state,
                metrics=metrics,
                react_trace=self.react_trace
            )

            # Publish final completed / failed event
            try:
                from app.core.events import event_publisher
                event_publisher.publish(self.execution_id, "completed" if status == "COMPLETED" else "failed", {"execution_id": self.execution_id, "status": status})
            except Exception:
                pass

            # Structured Logging
            try:
                from app.core.logging import log_structured_event
                log_structured_event(
                    event="execution_completed",
                    execution_id=self.execution_id,
                    provider=self.provider,
                    duration=duration,
                    status=status
                )
            except Exception:
                pass

            # Await all pending background memory tasks BEFORE saving execution summary
            await self._flush_pending_memory_tasks()

            # Save execution summary to memory
            if self.memory_manager:
                try:
                    exec_error = None
                    if self.state_mgr.state.failed_tasks:
                        exec_error = f"Failed tasks: {self.state_mgr.state.failed_tasks}"
                    async with self._memory_lock:
                        await self.memory_manager.save_execution(
                            execution_id=self.execution_id,
                            goal=self.plan.goal,
                            status=response.status,
                            tasks=self.plan.tasks,
                            duration=duration,
                            error=exec_error
                        )
                except Exception as e:
                    logger.warning(f"Failed to save execution summary to memory: {e}")

            return response
            
        except asyncio.CancelledError as ce:
            # Propagate cancelled event
            try:
                from app.core.events import event_publisher
                event_publisher.publish(self.execution_id, "cancelled", {"execution_id": self.execution_id})
            except Exception:
                pass
            raise ce
        except Exception as err:
            # Publish failed event on top-level errors
            try:
                from app.core.events import event_publisher
                event_publisher.publish(self.execution_id, "failed", {"execution_id": self.execution_id, "error": str(err)})
            except Exception:
                pass
            raise err
        finally:
            await self._flush_pending_memory_tasks()
