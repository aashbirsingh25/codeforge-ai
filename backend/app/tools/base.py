import time
import logging
from abc import ABC, abstractmethod
from functools import wraps
from typing import Type
from pydantic import BaseModel, ValidationError

from app.tools.exceptions import ToolValidationError, ToolExecutionError, ToolError

logger = logging.getLogger("app.tools")


def wrap_tool_execute(func):
    """Decorator to automatically wrap tool execution with input/output validation,

    timing, and structured logging.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        tool_name = getattr(self, "tool_name", self.__class__.__name__)
        start_time = time.perf_counter()
        success = False
        error_type = None

        try:
            # 1. Validate inputs against input_schema
            try:
                validated_input = self.input_schema(**kwargs)
            except ValidationError as ve:
                raise ToolValidationError(f"Input validation failed for tool '{tool_name}': {str(ve)}") from ve

            # 2. Call target execute method
            try:
                # We pass the validated inputs as keyword arguments to execute
                result = func(self, *args, **validated_input.model_dump())
            except ToolError:
                # Re-raise known tool framework exceptions
                raise
            except Exception as e:
                # Wrap any unexpected execution exceptions
                raise ToolExecutionError(f"Error during tool execution: {str(e)}") from e

            # 3. Validate output against output_schema
            if not isinstance(result, self.output_schema):
                raise ToolValidationError(
                    f"Tool '{tool_name}' output error: expected {self.output_schema.__name__}, "
                    f"got {type(result).__name__}"
                )

            success = True
            return result

        except Exception as e:
            error_type = type(e).__name__
            raise
        finally:
            duration = time.perf_counter() - start_time
            # Log structured metrics. We DO NOT log args/kwargs/results to prevent leaking secrets.
            logger.info(
                f"Tool Invocation: tool={tool_name} duration={duration:.4f}s success={success} error={error_type}",
                extra={
                    "tool_name": tool_name,
                    "duration_seconds": duration,
                    "success": success,
                    "error_type": error_type,
                }
            )

    return wrapper


class BaseTool(ABC):
    """Abstract base class that all tools must inherit from."""
    tool_name: str
    description: str
    category: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]

    def __init_subclass__(cls, **kwargs):
        """Automatically wrap the execute method in subclasses to enforce validation and logging."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "execute") and not getattr(cls.execute, "__isabstractmethod__", False):
            cls.execute = wrap_tool_execute(cls.execute)

    @abstractmethod
    def execute(self, **kwargs) -> BaseModel:
        """Executes the tool with validated kwargs and returns a response model."""
        pass
