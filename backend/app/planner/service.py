import time
import logging
from typing import List, Dict, Optional

from app.planner.schemas import PlanningRequest, PlanningResponse, ExecutionPlan
from app.planner.exceptions import PlanningError, PlanningStrategyError, PlanningValidationError
from app.planner.strategy import BasePlanningStrategy, SequentialPlanningStrategy, HierarchicalPlanningStrategy
from app.planner.planner import Planner
from app.llm.factory import ProviderFactory
from app.llm.schemas import ChatCompletionRequest, ChatMessage
from app.llm.exceptions import LLMException
from app.memory.manager import MemoryManager

logger = logging.getLogger("app.planner")


class PlannerService:
    """Orchestrates plan generation: Prompt -> LLM -> Parser -> Validator -> Response."""

    def __init__(self):
        # Setup supported strategies
        self._strategies: Dict[str, BasePlanningStrategy] = {
            "sequential": SequentialPlanningStrategy(),
            "hierarchical": HierarchicalPlanningStrategy()
        }

    def list_strategies(self) -> List[str]:
        """Lists names of all available planning strategies."""
        return list(self._strategies.keys())

    async def generate_plan(
        self,
        request: PlanningRequest,
        memory_manager: Optional[MemoryManager] = None
    ) -> PlanningResponse:
        """Asynchronously calls the LLM provider to construct a validated ExecutionPlan."""
        start_time = time.perf_counter()
        
        # 1. Resolve strategy
        strategy_name = (request.strategy or "sequential").lower().strip()
        strategy = self._strategies.get(strategy_name)
        if not strategy:
            raise PlanningStrategyError(f"Unsupported planning strategy: '{strategy_name}'")

        # 2. Resolve LLM provider
        provider_name = (request.provider or "gemini").lower().strip()
        try:
            provider = ProviderFactory.get_provider(provider_name)
        except ValueError as e:
            raise PlanningStrategyError(f"Failed to load provider: {str(e)}") from e

        # Determine default model to run
        from app.core.config import settings
        if provider_name == "gemini":
            model_name = settings.GEMINI_MODEL
        elif provider_name == "openai":
            model_name = settings.OPENAI_MODEL
        else:
            model_name = settings.GEMINI_MODEL

        # 3. Initialize Planner and construct prompts
        planner = Planner(strategy)
        system_prompt, user_prompt = planner.get_prompts(request.goal)

        # Query MemoryManager & retrieve relevant previous context
        if memory_manager:
            try:
                from app.memory.service import MemoryService
                mem_service = MemoryService(manager=memory_manager)
                memory_context = await mem_service.get_planning_context(request.goal)
                if memory_context:
                    user_prompt += f"\n\n### RELEVANT PREVIOUS CONTEXT & MEMORY\n{memory_context}"
            except Exception as e:
                logger.warning(f"Failed to retrieve planning memory context: {e}")

        chat_request = ChatCompletionRequest(
            model=model_name,
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt)
            ]
        )

        try:
            # 4. Generate LLM response
            chat_response = await provider.generate(chat_request)
            raw_response = chat_response.content
        except LLMException as e:
            duration = time.perf_counter() - start_time
            logger.error(
                f"LLM call failed: provider={provider_name} strategy={strategy_name} "
                f"duration={duration:.4f}s error={type(e).__name__}"
            )
            raise
        except Exception as e:
            # Log failure
            duration = time.perf_counter() - start_time
            logger.error(
                f"LLM call failed: provider={provider_name} strategy={strategy_name} "
                f"duration={duration:.4f}s error={type(e).__name__}"
            )
            raise PlanningError(f"LLM Generation call failed: {str(e)}") from e

        # 5. Parse and Validate using internal Planner class
        try:
            plan = planner.parse_and_validate(raw_response)
        except Exception as e:
            # Log parsing/validation failures
            duration = time.perf_counter() - start_time
            logger.error(
                f"Plan verification failed: provider={provider_name} strategy={strategy_name} "
                f"duration={duration:.4f}s error={type(e).__name__} details={str(e)}"
            )
            raise

        duration = time.perf_counter() - start_time
        
        # Save successful plan to memory
        if memory_manager:
            try:
                await memory_manager.save_plan(goal=request.goal, plan=plan)
            except Exception as e:
                logger.warning(f"Failed to save plan to memory: {e}")

        # 6. Structured log of success
        logger.info(
            f"Execution plan completed: provider={provider_name} strategy={strategy_name} "
            f"tasks={len(plan.tasks)} duration={duration:.4f}s"
        )

        return PlanningResponse(
            plan=plan,
            strategy=strategy_name,
            provider=provider_name,
            duration_seconds=duration
        )
