from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Complexity(str, Enum):
    TRIVIAL = "TRIVIAL"
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    VERY_HARD = "VERY_HARD"


class Goal(BaseModel):
    text: str = Field(..., description="The user's high-level goal description")


class SubTask(BaseModel):
    id: str = Field(..., description="Unique subtask identifier")
    title: str = Field(..., description="Short title of the subtask")
    description: str = Field(..., description="Detailed description of what needs to be done")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Current execution status of the subtask")


class Task(BaseModel):
    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Short title of the task")
    description: str = Field(..., description="Detailed description of what needs to be done")
    priority: TaskPriority = Field(..., description="Task priority level")
    estimated_complexity: Complexity = Field(..., description="Complexity assessment")
    estimated_duration: str = Field(..., description="Estimated time duration (e.g. '2 hours', '30m')")
    dependencies: List[str] = Field(default_factory=list, description="List of task IDs this task depends on")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Current status of the task")
    subtasks: List[SubTask] = Field(default_factory=list, description="Subtasks breakdown")


class ExecutionPlan(BaseModel):
    goal: str = Field(..., description="The original high-level goal text")
    tasks: List[Task] = Field(..., description="List of tasks in the plan")


class PlanningRequest(BaseModel):
    goal: str = Field(..., description="High-level goal string")
    strategy: Optional[str] = Field(None, description="The planning strategy to use (e.g. 'sequential', 'hierarchical')")
    provider: Optional[str] = Field(None, description="LLM Provider to use (e.g. 'gemini', 'openai')")


class PlanningResponse(BaseModel):
    plan: ExecutionPlan = Field(..., description="The generated execution plan")
    strategy: str = Field(..., description="The strategy used")
    provider: str = Field(..., description="The LLM provider used")
    duration_seconds: float = Field(..., description="Duration taken to generate and validate the plan")
