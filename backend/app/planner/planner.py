from app.planner.strategy import BasePlanningStrategy
from app.planner.parser import PlanParser
from app.planner.validator import PlanValidator
from app.planner.schemas import ExecutionPlan


class Planner:
    """Core Planner engine that generates prompt templates and runs parsing

    and topological validation on LLM response strings.
    """
    def __init__(self, strategy: BasePlanningStrategy):
        self.strategy = strategy
        self.parser = PlanParser()
        self.validator = PlanValidator()

    def get_prompts(self, goal: str) -> tuple[str, str]:
        """Generates system and user prompt strings tailored to the loaded strategy."""
        system_prompt = self.strategy.get_system_prompt()
        user_prompt = self.strategy.get_user_prompt(goal)
        return system_prompt, user_prompt

    def parse_and_validate(self, raw_response: str) -> ExecutionPlan:
        """Parses the raw text response, maps to ExecutionPlan schema,

        and executes cycle/constraint validation rules.
        """
        # 1. Parse JSON
        parsed_dict = self.parser.parse(raw_response)

        # 2. Schema instantiation (validates types, Enums, required fields)
        plan = ExecutionPlan(**parsed_dict)

        # 3. Deep custom constraint checking (dependencies, uniqueness, loops)
        self.validator.validate(plan)

        return plan
