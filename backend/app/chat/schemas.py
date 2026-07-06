from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user message to send to the assistant")

class ChatResponse(BaseModel):
    response: str = Field(..., description="The assistant's text response")
    provider: str = Field(..., description="The LLM provider name used")
    duration_seconds: float = Field(..., description="Execution duration in seconds")

class ChatHistoryMessage(BaseModel):
    role: str = Field(..., description="Role: user or assistant")
    content: str = Field(..., description="Content of the message")
    timestamp: str = Field(..., description="ISO-8601 timestamp string representing message generation time")
