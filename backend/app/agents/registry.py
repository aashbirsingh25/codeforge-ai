import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Type, Any, Optional

from app.agents.schemas import AgentResult, AgentAction, AgentObservation
from app.agents.exceptions import AgentExecutionError
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
        max_steps = 5
        step_idx = 0
        action_recorder = context.get("action_recorder")
        
        while step_idx < max_steps:
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

            try:
                chat_res = await provider.generate(chat_req)
                response_text = chat_res.content
            except LLMException:
                raise
            except Exception as e:
                logger.error(f"Executor LLM generation failed: {e}")
                return AgentResult(success=False, error=f"LLM generation failed: {str(e)}")

            # Parse JSON response
            try:
                clean_text = response_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                
                decision = json.loads(clean_text)
            except Exception as e:
                logger.warning(f"Failed to parse agent decision JSON: {e}. Raw response: {response_text}")
                history_lines.append(f"System Error: Your response was not valid JSON. Error: {str(e)}. Please retry and output valid JSON.")
                continue

            action_type = decision.get("action")
            thought = decision.get("thought", "")
            logger.info(f"Agent thought: {thought}")

            if action_type == "finish":
                success = decision.get("success", True)
                output = decision.get("output", "")
                return AgentResult(success=success, output=output)

            elif action_type == "call_tool":
                tool_name = decision.get("tool_name")
                tool_args = decision.get("tool_args", {})
                
                agent_action = AgentAction(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    description=thought
                )
                
                obs_content = ""
                obs_success = False
                obs_error = None

                try:
                    if not tool_registry.has_tool(tool_name):
                        raise AgentExecutionError(f"Tool '{tool_name}' not found in registry.")
                    
                    tool_inst = tool_registry.get_tool(tool_name)
                    tool_res = tool_inst.execute(**tool_args)
                    obs_content = tool_res.model_dump_json() if hasattr(tool_res, "model_dump_json") else str(tool_res)
                    obs_success = True
                except Exception as ex:
                    logger.error(f"Tool '{tool_name}' execution failed: {ex}")
                    obs_content = ""
                    obs_success = False
                    obs_error = str(ex)

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

            else:
                history_lines.append(f"System Error: Unknown action type '{action_type}'. Valid actions are 'call_tool' and 'finish'.")

        return AgentResult(success=False, error="Agent execution exceeded maximum ReAct steps (5) without completing.")


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
