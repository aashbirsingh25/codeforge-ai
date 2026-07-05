import logging
from typing import List, Dict, Any, Callable, Optional
from app.tools.base import registry
from app.llm.providers.llm import LLMService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are CodeForge AI, an autonomous software engineering agent.
Your goal is to understand requirements, plan tasks, write code, run tests, debug failures, and iteratively improve the codebase.
"""

class AgentLoop:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.tools = registry.list_tools()

    def run(
        self,
        task: str,
        step_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        max_steps: int = 15
    ) -> Dict[str, Any]:
        """
        Internal ReAct execution loop (unexposed to API).
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Please complete the following task:\n\n{task}"}
        ]
        
        steps = []
        final_answer = None

        if step_callback:
            step_callback("start", {"task": task})

        for step in range(1, max_steps + 1):
            if step_callback:
                step_callback("step_start", {"step": step})

            try:
                response = self.llm_service.generate(messages, tools=self.tools)
            except Exception as e:
                error_msg = f"LLM generation failed: {str(e)}"
                if step_callback:
                    step_callback("error", {"message": error_msg})
                return {"success": False, "error": error_msg, "steps": steps}

            thought = response.get("content")
            tool_calls = response.get("tool_calls")

            if thought:
                if step_callback:
                    step_callback("thought", {"content": thought})

            if tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": thought,
                    "tool_calls": tool_calls
                })

                for tc in tool_calls:
                    tc_id = tc["id"]
                    tool_name = tc["name"]
                    tool_args = tc["arguments"]

                    if step_callback:
                        step_callback("action", {"tool": tool_name, "arguments": tool_args})

                    tool_obj = registry.get_tool(tool_name)
                    if not tool_obj:
                        observation = f"Error: Tool '{tool_name}' not found."
                    else:
                        try:
                            observation = tool_obj.execute(**tool_args)
                        except Exception as e:
                            observation = f"Error executing tool '{tool_name}': {str(e)}"

                    if step_callback:
                        step_callback("observation", {"tool": tool_name, "result": observation})

                    steps.append({
                        "step": step,
                        "thought": thought,
                        "tool": tool_name,
                        "arguments": tool_args,
                        "observation": observation
                    })

                    messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "tool_call_id": tc_id,
                        "content": observation
                    })
            else:
                final_answer = thought
                messages.append({
                    "role": "assistant",
                    "content": final_answer
                })
                
                if step_callback:
                    step_callback("final_answer", {"content": final_answer})
                
                steps.append({
                    "step": step,
                    "thought": final_answer,
                    "tool": None,
                    "arguments": None,
                    "observation": None
                })
                break
        
        if not final_answer:
            final_answer = "Max execution steps reached."
            if step_callback:
                step_callback("final_answer", {"content": final_answer})

        return {
            "success": True,
            "final_answer": final_answer,
            "steps": steps
        }
