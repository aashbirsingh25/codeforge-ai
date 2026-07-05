from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class GenerationConfig(BaseModel):
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature.")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling probability.")
    max_tokens: Optional[int] = Field(None, gt=0, description="Max tokens to generate.")

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(..., description="Role of the message author.")
    content: str = Field(..., description="Content of the message.")

class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model string name.")
    messages: List[ChatMessage] = Field(..., description="Chat message history.")
    config: Optional[GenerationConfig] = Field(None, description="Optional model configurations parameters.")

class ChatCompletionResponse(BaseModel):
    content: str = Field(..., description="Generated text content.")
    model: str = Field(..., description="Model identifier used for generation.")
    usage: Optional[Dict[str, int]] = Field(None, description="Token consumption stats if available.")

class ProviderInfo(BaseModel):
    name: str = Field(..., description="Name of LLM provider.")
    available_models: List[str] = Field(..., description="List of supported models.")
    is_configured: bool = Field(..., description="True if API keys are configured.")

class ProviderHealthResponse(BaseModel):
    provider: str = Field(..., description="Name of provider.")
    status: Literal["healthy", "unhealthy"] = Field(..., description="Operational status.")
    error_message: Optional[str] = Field(None, description="Error message details if unhealthy.")
