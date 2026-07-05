from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.tools.registry import registry

router = APIRouter()


class ToolMetadata(BaseModel):
    name: str = Field(..., description="Unique machine-readable name of the tool")
    description: str = Field(..., description="Human-readable description of what the tool does")
    category: str = Field(..., description="The category classification (e.g. filesystem, terminal, git)")
    input_schema: Dict[str, Any] = Field(..., description="Pydantic JSON schema for the tool inputs")
    output_schema: Dict[str, Any] = Field(..., description="Pydantic JSON schema for the tool outputs")


@router.get("", response_model=List[ToolMetadata])
def list_tools():
    """List metadata for all registered tools."""
    tools = registry.list_tools()
    metadata_list = []
    for tool in tools:
        try:
            input_schema = tool.input_schema.model_json_schema()
        except Exception:
            input_schema = {}
            
        try:
            output_schema = tool.output_schema.model_json_schema()
        except Exception:
            output_schema = {}

        metadata_list.append(
            ToolMetadata(
                name=tool.tool_name,
                description=tool.description,
                category=tool.category,
                input_schema=input_schema,
                output_schema=output_schema
            )
        )
    return metadata_list


@router.get("/{tool_name}", response_model=ToolMetadata)
def get_tool_metadata(tool_name: str):
    """Retrieve metadata for a specific tool by name."""
    if not registry.has_tool(tool_name):
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found."
        )
    
    tool = registry.get_tool(tool_name)
    try:
        input_schema = tool.input_schema.model_json_schema()
    except Exception:
        input_schema = {}
        
    try:
        output_schema = tool.output_schema.model_json_schema()
    except Exception:
        output_schema = {}

    return ToolMetadata(
        name=tool.tool_name,
        description=tool.description,
        category=tool.category,
        input_schema=input_schema,
        output_schema=output_schema
    )
