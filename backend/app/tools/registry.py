import logging
import importlib
import pkgutil
from typing import Dict, List

from app.tools.base import BaseTool
from app.tools.exceptions import ToolValidationError

logger = logging.getLogger("app.tools")


class ToolRegistry:
    """Registry to manage and look up available tools.

    Supports dynamic plugin discovery.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance.

        If a tool with the same name exists, it is overwritten.
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Expected BaseTool instance, got {type(tool).__name__}")
        
        self._tools[tool.tool_name] = tool
        logger.info(f"Registered tool: {tool.tool_name} (Category: {tool.category})")

    def unregister(self, tool_name: str) -> None:
        """Unregisters a tool by name."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")

    def get_tool(self, name: str) -> BaseTool:
        """Looks up a tool by name. Raises ToolValidationError if not found."""
        if name not in self._tools:
            raise ToolValidationError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def has_tool(self, name: str) -> bool:
        """Checks if a tool is registered."""
        return name in self._tools

    def list_tools(self) -> List[BaseTool]:
        """Lists all registered tools."""
        return list(self._tools.values())

    def discover_tools(self, package_names: List[str]) -> None:
        """Scans packages and submodules dynamically to discover and register

        classes inheriting from BaseTool.
        """
        for pkg_name in package_names:
            try:
                package = importlib.import_module(pkg_name)
            except ImportError as e:
                logger.error(f"Failed to import package '{pkg_name}' for discovery: {e}")
                continue

            if not hasattr(package, "__path__"):
                # Single module discovery
                self._register_from_module(package)
                continue

            for _, mod_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
                try:
                    module = importlib.import_module(mod_name)
                    self._register_from_module(module)
                except Exception as e:
                    logger.error(f"Error importing module '{mod_name}' during discovery: {e}")

    def _register_from_module(self, module) -> None:
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseTool)
                and attr is not BaseTool
                and not getattr(attr, "__isabstractmethod__", False)
                and not attr.__name__.startswith("Base")
            ):
                try:
                    # Instantiate with no args (using class defaults)
                    tool_instance = attr()
                    self.register(tool_instance)
                except Exception as e:
                    logger.warning(
                        f"Could not auto-instantiate tool class '{attr.__name__}' from '{module.__name__}': {e}"
                    )


# Global registry instance
registry = ToolRegistry()
