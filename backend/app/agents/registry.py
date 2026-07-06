import logging
import json
import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Type, Any, Optional

from app.agents.schemas import (
    AgentResult,
    AgentAction,
    AgentObservation,
    Thought,
    Action,
    Observation,
    ReActStep,
    ReActTrace
)
from app.agents.exceptions import (
    AgentExecutionError,
    AgentTimeoutError,
    AgentMaxIterationsError,
    AgentMaxToolCallsError,
    AgentRecursionError,
    AgentInvalidToolError
)
from app.llm.factory import ProviderFactory
from app.core.config import settings
from app.tools.registry import registry as tool_registry
from app.agents.prompts import AGENT_SYSTEM_PROMPT, AGENT_USER_PROMPT
from app.llm.schemas import ChatCompletionRequest, ChatMessage
from app.llm.exceptions import LLMException


logger = logging.getLogger("app.agents.registry")

class BaseAgent(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the agent."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the agent does."""
        pass

    @abstractmethod
    async def execute(self, task_id: str, context: Dict[str, Any], *args, **kwargs) -> AgentResult:
        """Execute a task and return the result."""
        pass


class PlannerAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "PlannerAgent"

    @property
    def description(self) -> str:
        return "Decomposes goals and refines execution plans."

    async def execute(self, task_id: str, context: Dict[str, Any], *args, **kwargs) -> AgentResult:
        # PlannerAgent can be used to generate/regenerate plans
        from app.planner.service import PlannerService
        from app.planner.schemas import PlanningRequest
        goal = context.get("goal")
        if not goal:
            return AgentResult(success=False, error="No goal provided in context for PlannerAgent.")
        
        try:
            planner_service = PlannerService()
            response = await planner_service.generate_plan(PlanningRequest(goal=goal))
            return AgentResult(success=True, output=response.plan.model_dump_json())
        except LLMException:
            raise
        except Exception as e:
            return AgentResult(success=False, error=str(e))


class ExecutorAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "ExecutorAgent"

    @property
    def description(self) -> str:
        return "Executes tasks by dynamically invoking workspace tools."

    async def execute(self, task_id: str, context: Dict[str, Any], *args, **kwargs) -> AgentResult:
        task = context.get("task")
        if not task:
            return AgentResult(success=False, error="No task provided in context for ExecutorAgent.")

        provider_name = context.get("provider") or "gemini"
        try:
            provider = ProviderFactory.get_provider(provider_name)
        except Exception as e:
            return AgentResult(success=False, error=f"Failed to load LLM provider '{provider_name}': {e}")

        # Resolve model name
        if provider_name == "gemini":
            model_name = settings.GEMINI_MODEL
        elif provider_name == "openai":
            model_name = settings.OPENAI_MODEL
        else:
            model_name = settings.GEMINI_MODEL

        # Resolve limits
        max_iters = kwargs.get("max_iterations") or context.get("max_iterations") or getattr(settings, "AGENT_MAX_ITERATIONS", 10)
        max_tools = kwargs.get("max_tool_calls") or context.get("max_tool_calls") or getattr(settings, "AGENT_MAX_TOOL_CALLS", 10)
        task_timeout = kwargs.get("timeout") or context.get("timeout") or getattr(settings, "AGENT_TIMEOUT", 120.0)
        rec_limit = kwargs.get("recursion_limit") or context.get("recursion_limit") or getattr(settings, "AGENT_RECURSION_LIMIT", 3)

        # Get trace callback if any
        react_trace_callback = context.get("react_trace_callback")
        propagate = kwargs.get("propagate_exceptions") or context.get("propagate_exceptions", False)

        # Get list of registered tools dynamically
        tools = tool_registry.list_tools()
        tools_desc = []
        for t in tools:
            try:
                schema_json = json.dumps(t.input_schema.model_json_schema(), indent=2)
            except Exception:
                schema_json = str(t.input_schema)
            tools_desc.append(f"Tool: {t.tool_name}\nDescription: {t.description}\nSchema:\n{schema_json}\n---")
        
        tools_description = "\n".join(tools_desc)
        system_prompt = AGENT_SYSTEM_PROMPT.format(tools_description=tools_description)

        history_lines = []
        step_idx = 0
        tool_calls_count = 0
        consecutive_identical_calls = 0
        last_tool_call = None
        action_recorder = context.get("action_recorder")

        # Run the iterative ReAct loop under timeout protection
        async def run_loop():
            nonlocal step_idx, tool_calls_count, consecutive_identical_calls, last_tool_call
            
            while True:
                step_start_time = time.perf_counter()
                
                # Check limits before starting iteration
                if step_idx >= max_iters:
                    raise AgentMaxIterationsError(f"Agent execution exceeded maximum ReAct steps ({max_iters}) without completing.")

                step_idx += 1
                history_str = "\n".join(history_lines) if history_lines else "No previous actions."
                user_prompt = AGENT_USER_PROMPT.format(
                    task_title=task.title,
                    task_description=task.description,
                    history=history_str
                )

                chat_req = ChatCompletionRequest(
                    model=model_name,
                    messages=[
                        ChatMessage(role="system", content=system_prompt),
                        ChatMessage(role="user", content=user_prompt)
                    ]
                )

                # Ask the LLM what to do next
                try:
                    chat_res = await provider.generate(chat_req)
                    response_text = chat_res.content
                except LLMException:
                    raise
                except Exception as e:
                    logger.error(f"Executor LLM generation failed: {e}")
                    raise AgentExecutionError(f"LLM generation failed: {str(e)}")

                # Parse JSON response
                decision = None
                parse_error = None
                try:
                    clean_text = response_text.strip()
                    if clean_text.startswith("```json"):
                        clean_text = clean_text[7:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]
                    clean_text = clean_text.strip()
                    
                    decision = json.loads(clean_text)
                except Exception as e:
                    parse_error = str(e)
                    logger.warning(f"Failed to parse agent decision JSON: {e}. Raw response: {response_text}")
                    
                step_duration = time.perf_counter() - step_start_time

                if parse_error:
                    # Record step trace for malformed response
                    step_thought = Thought(reasoning=f"Malformed LLM response: {response_text[:200]}")
                    step_observation = Observation(
                        content="",
                        success=False,
                        error=f"System Error: Your response was not valid JSON. Error: {parse_error}. Please retry and output valid JSON."
                    )
                    react_step = ReActStep(
                        thought=step_thought,
                        action=None,
                        observation=step_observation,
                        duration_seconds=step_duration
                    )
                    if react_trace_callback:
                        react_trace_callback(react_step)

                    # Feed the parsing error back into the next reasoning step
                    history_lines.append(step_observation.error)
                    continue

                # Process parsed decision
                action_type = decision.get("action")
                thought_text = decision.get("thought", "")
                logger.info(f"Agent thought: {thought_text}")

                step_thought = Thought(reasoning=thought_text)

                if action_type == "finish":
                    # Record final finish step trace
                    react_step = ReActStep(
                        thought=step_thought,
                        action=None,
                        observation=None,
                        duration_seconds=step_duration
                    )
                    if react_trace_callback:
                        react_trace_callback(react_step)

                    success = decision.get("success", True)
                    output = decision.get("output", "")
                    return AgentResult(success=success, output=output)

                elif action_type == "call_tool":
                    # Check tool calls limit
                    if tool_calls_count >= max_tools:
                        raise AgentMaxToolCallsError(f"Agent execution exceeded maximum tool calls ({max_tools}).")

                    tool_name = decision.get("tool_name")
                    tool_args = decision.get("tool_args", {})
                    
                    step_action = Action(tool_name=tool_name, tool_args=tool_args)

                    # Recursion/Loop protection
                    current_call = (tool_name, json.dumps(tool_args, sort_keys=True))
                    if last_tool_call == current_call:
                        consecutive_identical_calls += 1
                    else:
                        consecutive_identical_calls = 1
                    last_tool_call = current_call

                    if consecutive_identical_calls > rec_limit:
                        raise AgentRecursionError(f"Recursion protection triggered: Tool '{tool_name}' called with same arguments {consecutive_identical_calls} times consecutively.")

                    # Also build AgentAction for action recorder compatibility
                    agent_action = AgentAction(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        description=thought_text
                    )

                    obs_content = ""
                    obs_success = False
                    obs_error = None

                    try:
                        # Validate tool name
                        if not tool_name or not tool_registry.has_tool(tool_name):
                            raise AgentInvalidToolError(f"Tool '{tool_name}' not found in registry.")

                        tool_calls_count += 1
                        tool_inst = tool_registry.get_tool(tool_name)
                        tool_res = tool_inst.execute(**tool_args)
                        obs_content = tool_res.model_dump_json() if hasattr(tool_res, "model_dump_json") else str(tool_res)
                        obs_success = True
                    except AgentInvalidToolError as ex:
                        obs_error = f"Tool '{tool_name}' not found in registry. Please choose from registered tools."
                        logger.error(f"Tool validation failed: {ex}")
                    except Exception as ex:
                        obs_error = str(ex)
                        logger.error(f"Tool '{tool_name}' execution failed: {ex}")

                    agent_obs = AgentObservation(
                        content=obs_content,
                        success=obs_success,
                        error=obs_error
                    )

                    if action_recorder:
                        action_recorder(agent_action, agent_obs)

                    status_str = "Success" if obs_success else f"Error: {obs_error}"
                    history_lines.append(
                        f"Action: Call tool '{tool_name}' with args {json.dumps(tool_args)}\n"
                        f"Result: {status_str}\n"
                        f"Observation: {obs_content if obs_success else obs_error}"
                    )

                    # Record step trace
                    step_observation = Observation(
                        content=obs_content,
                        success=obs_success,
                        error=obs_error
                    )
                    react_step = ReActStep(
                        thought=step_thought,
                        action=step_action,
                        observation=step_observation,
                        duration_seconds=step_duration
                    )
                    if react_trace_callback:
                        react_trace_callback(react_step)

                else:
                    # Unknown action type, feed error back to LLM
                    err_msg = f"System Error: Unknown action type '{action_type}'. Valid actions are 'call_tool' and 'finish'."
                    history_lines.append(err_msg)
                    
                    # Record step trace
                    step_observation = Observation(
                        content="",
                        success=False,
                        error=err_msg
                    )
                    react_step = ReActStep(
                        thought=step_thought,
                        action=None,
                        observation=step_observation,
                        duration_seconds=step_duration
                    )
                    if react_trace_callback:
                        react_trace_callback(react_step)

        # Enforce timeout and exceptions propagation
        try:
            try:
                return await asyncio.wait_for(run_loop(), timeout=task_timeout)
            except asyncio.TimeoutError as te:
                logger.error(f"Agent execution timed out for task {task_id}")
                raise AgentTimeoutError(f"Agent execution timed out after {task_timeout} seconds.") from te
        except (AgentMaxIterationsError, AgentMaxToolCallsError, AgentRecursionError, AgentTimeoutError, AgentInvalidToolError) as ex:
            if propagate:
                raise
            return AgentResult(success=False, error=str(ex))
        except AgentExecutionError as ex:
            if propagate:
                raise
            return AgentResult(success=False, error=str(ex))




class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, Type[BaseAgent]] = {}

    def register(self, agent_cls: Type[BaseAgent]) -> None:
        if not issubclass(agent_cls, BaseAgent):
            raise TypeError(f"Expected class inheriting from BaseAgent, got {agent_cls}")
        name = agent_cls.__name__
        self._agents[name.lower()] = agent_cls
        logger.info(f"Registered agent: {name}")

    def get_agent(self, name: str) -> BaseAgent:
        name_lower = name.lower()
        if name_lower not in self._agents:
            raise AgentExecutionError(f"Agent '{name}' is not registered.")
        return self._agents[name_lower]()

    def list_agents(self) -> list:
        return list(self._agents.keys())


agent_registry = AgentRegistry()
agent_registry.register(PlannerAgent)
agent_registry.register(ExecutorAgent)
