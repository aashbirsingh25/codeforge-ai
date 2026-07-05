from abc import ABC, abstractmethod
from app.planner.prompts import (
    SEQUENTIAL_STRATEGY_SYSTEM,
    HIERARCHICAL_STRATEGY_SYSTEM,
    USER_GOAL_PROMPT
)


class BasePlanningStrategy(ABC):
    """Abstract base class for all planning strategies."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the registered name of the strategy."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Generates the system prompt instructions for the LLM."""
        pass

    def get_user_prompt(self, goal: str) -> str:
        """Generates the user prompt based on the user's high-level goal."""
        return USER_GOAL_PROMPT.format(goal=goal)


class SequentialPlanningStrategy(BasePlanningStrategy):
    """Strategy that guides the LLM to create a strict linear step-by-step sequence."""
    
    @property
    def name(self) -> str:
        return "sequential"

    def get_system_prompt(self) -> str:
        return SEQUENTIAL_STRATEGY_SYSTEM


class HierarchicalPlanningStrategy(BasePlanningStrategy):
    """Strategy that guides the LLM to construct a phased, hierarchical task structure."""
    
    @property
    def name(self) -> str:
        return "hierarchical"

    def get_system_prompt(self) -> str:
        return HIERARCHICAL_STRATEGY_SYSTEM
