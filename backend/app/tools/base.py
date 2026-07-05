import inspect
from typing import Callable, Any, Dict, Type, List
from pydantic import BaseModel, create_model

class Tool:
    def __init__(self, name: str, description: str, func: Callable, args_schema: Type[BaseModel]):
        self.name = name
        self.description = description
        self.func = func
        self.args_schema = args_schema

    def execute(self, **kwargs) -> Any:
        validated_args = self.args_schema(**kwargs)
        return self.func(**validated_args.model_dump())

    def to_openai_format(self) -> Dict[str, Any]:
        schema = self.args_schema.model_json_schema()
        schema.pop("title", None)
        if "properties" in schema:
            for prop in schema["properties"].values():
                if isinstance(prop, dict):
                    prop.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema
            }
        }

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str | None = None, description: str | None = None):
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_desc = description or func.__doc__ or f"Execute tool {tool_name}"
            
            sig = inspect.signature(func)
            fields = {}
            for param_name, param in sig.parameters.items():
                if param.annotation == inspect.Parameter.empty:
                    annotation = str
                else:
                    annotation = param.annotation
                    
                default = param.default if param.default != inspect.Parameter.empty else ...
                fields[param_name] = (annotation, default)
                
            model_name = f"{tool_name}_input"
            args_schema = create_model(model_name, **fields)
            
            tool = Tool(name=tool_name, description=tool_desc, func=func, args_schema=args_schema)
            self._tools[tool_name] = tool
            return func
        return decorator

    def get_tool(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def to_openai_tools(self) -> List[Dict[str, Any]]:
        return [t.to_openai_format() for t in self._tools.values()]

registry = ToolRegistry()
