from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.planner.schemas import ExecutionPlan

class AgentAction(BaseModel):
    tool_name: str = Field(..., description="Name of the tool being called")
    tool_args: Dict[str, Any] = Field(..., description="Arguments passed to the tool")
    description: Optional[str] = Field(None, description="Optional description of why the action is taken")

class AgentObservation(BaseModel):
    content: str = Field(..., description="Stringified output/result of the action")
    success: bool = Field(..., description="Whether the action succeeded or failed")
    error: Optional[str] = Field(None, description="Error message, if any")

class AgentResult(BaseModel):
    success: bool = Field(..., description="Whether the agent achieved its goal for the task")
    output: Optional[str] = Field(None, description="The final text output/result of the agent")
    error: Optional[str] = Field(None, description="Error message, if any")

class ExecutionStep(BaseModel):
    task_id: str = Field(..., description="The ID of the task being executed")
    status: str = Field(..., description="Current status of the step (e.g. COMPLETED, FAILED, RUNNING)")
    actions: List[AgentAction] = Field(default_factory=list, description="Actions taken in this step")
    observations: List[AgentObservation] = Field(default_factory=list, description="Observations gathered in this step")
    retry_count: int = Field(0, description="Number of retries attempted for this task")
    error: Optional[str] = Field(None, description="Error details, if any")
    start_time: Optional[str] = Field(None, description="ISO timestamp for when the task started")
    end_time: Optional[str] = Field(None, description="ISO timestamp for when the task ended")

class ExecutionState(BaseModel):
    current_task: Optional[str] = Field(None, description="The ID of the task currently being executed")
    completed_tasks: List[str] = Field(default_factory=list, description="List of completed task IDs")
    failed_tasks: List[str] = Field(default_factory=list, description="List of failed task IDs")
    pending_tasks: List[str] = Field(default_factory=list, description="List of pending task IDs")
    observations: Dict[str, List[AgentObservation]] = Field(default_factory=dict, description="Observations accumulated per task")
    execution_history: List[ExecutionStep] = Field(default_factory=list, description="History of execution steps")
    timestamps: Dict[str, Any] = Field(default_factory=dict, description="Start/End timestamps for tasks and overall engine execution")
    retry_count: Dict[str, int] = Field(default_factory=dict, description="Retry count per task")

class ExecutionRequest(BaseModel):
    goal: Optional[str] = Field(None, description="Raw goal string to execute (generates a plan)")
    plan: Optional[ExecutionPlan] = Field(None, description="An existing execution plan to run")

class ExecutionMetrics(BaseModel):
    start_time: str = Field(..., description="ISO timestamp when execution started")
    end_time: Optional[str] = Field(None, description="ISO timestamp when execution ended")
    duration_seconds: Optional[float] = Field(None, description="Total execution duration in seconds")
    retry_count: int = Field(0, description="Total retries across all tasks")

class ExecutionResponse(BaseModel):
    execution_id: str = Field(..., description="Unique ID for this execution run")
    status: str = Field(..., description="Overall execution status")
    plan: ExecutionPlan = Field(..., description="The plan that was executed")
    state: ExecutionState = Field(..., description="Final/current execution state details")
    metrics: ExecutionMetrics = Field(..., description="Performance and retry metrics")
