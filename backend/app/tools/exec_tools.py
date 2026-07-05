import subprocess
from app.core.config import settings
from app.tools.base import registry

@registry.register(
    name="terminal_run",
    description="Execute a terminal command in the workspace directory. Returns standard output and standard error."
)
def terminal_run(command: str) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=settings.WORKSPACE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=45.0
        )
        
        output = []
        if result.stdout:
            output.append(f"--- STDOUT ---\n{result.stdout}")
        if result.stderr:
            output.append(f"--- STDERR ---\n{result.stderr}")
        
        output.append(f"Exit Code: {result.returncode}")
        return "\n".join(output)
        
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out after 45 seconds."
    except Exception as e:
        return f"Error executing command '{command}': {str(e)}"
