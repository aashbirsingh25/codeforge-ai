import sys
import subprocess
import tempfile
import os
from pathlib import Path
from app.tools.base import BaseTool
from app.workspace import workspace_manager
from app.tools.schemas import ExecutePythonRequest, ExecutePythonResponse
from app.tools.exceptions import ToolExecutionError

class ExecutePythonTool(BaseTool):
    tool_name = "execute_python"
    description = "Execute Python code safely in a subprocess and return stdout, stderr, exit code, and timeout status."
    category = "execution"
    input_schema = ExecutePythonRequest
    output_schema = ExecutePythonResponse

    def execute(self, code: str, timeout: float = 30.0) -> ExecutePythonResponse:
        # Create a temporary file in the system temp directory
        fd, temp_path_str = tempfile.mkstemp(suffix=".py")
        temp_path = Path(temp_path_str)
        try:
            # Write the code to the temp file
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Execute python script inside a subprocess
            # Set working directory to workspace root to restrict it to workspace
            cwd = workspace_manager.workspace_root
            
            # Run the command
            result = subprocess.run(
                [sys.executable, str(temp_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            return ExecutePythonResponse(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                timeout_expired=False
            )
            
        except subprocess.TimeoutExpired as te:
            # Capture output if possible
            stdout_str = te.stdout.decode('utf-8', errors='ignore') if isinstance(te.stdout, bytes) else (te.stdout or "")
            stderr_str = te.stderr.decode('utf-8', errors='ignore') if isinstance(te.stderr, bytes) else (te.stderr or "")
            return ExecutePythonResponse(
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=-1,
                timeout_expired=True
            )
        except Exception as e:
            raise ToolExecutionError(f"Subprocess execution failed: {str(e)}") from e
        finally:
            # Ensure the temp file is cleaned up
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
