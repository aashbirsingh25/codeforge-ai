import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.tools.base import BaseTool
from app.tools.schemas import GenerateCodeRequest, GenerateCodeResponse

def run_async(coro):
    """Runs a coroutine synchronously in a separate thread/event loop."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coro)).result()

class GenerateCodeTool(BaseTool):
    tool_name = "generate_code"
    description = "Generate clean Python code from natural language requirements."
    category = "codegen"
    input_schema = GenerateCodeRequest
    output_schema = GenerateCodeResponse

    def execute(self, requirements: str, language: str = "python") -> GenerateCodeResponse:
        try:
            from app.agents.registry import agent_registry
            agent = agent_registry.get_agent("CodeGenerationAgent")
            context = {
                "requirements": requirements,
                "provider": "gemini"
            }
            # Execute the agent synchronously via run_async
            res = run_async(agent.execute("codegen_task", context))
            if res.success:
                return GenerateCodeResponse(code=res.output, success=True)
            else:
                from app.tools.exceptions import ToolExecutionError
                raise ToolExecutionError(res.error or "Code generation failed.")
        except Exception as e:
            from app.tools.exceptions import ToolExecutionError
            raise ToolExecutionError(str(e)) from e
