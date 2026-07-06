from typing import List
from fastapi import APIRouter, status, Depends
from app.chat.schemas import ChatRequest, ChatResponse, ChatHistoryMessage
from app.chat.service import ChatService

router = APIRouter()

def get_chat_service() -> ChatService:
    return ChatService()

@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the assistant",
    description="Accepts a user query, fetches context (executions, plans, tools) from memory, retrieves history, requests completions from the active LLM provider, and logs entries.",
    responses={
        200: {
            "description": "Successfully completed assistant response",
            "content": {
                "application/json": {
                    "example": {
                        "response": "Here is how you can build a FastAPI chat server...",
                        "provider": "gemini",
                        "duration_seconds": 1.15
                    }
                }
            }
        }
    }
)
async def send_chat_message(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service)
):
    return await service.send_message(request.message)

@router.get(
    "/history",
    response_model=List[ChatHistoryMessage],
    status_code=status.HTTP_200_OK,
    summary="Get recent chat logs",
    description="Retrieve the chronological message logs of user prompts and corresponding assistant answers.",
    responses={
        200: {
            "description": "Chronological history logs",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "role": "user",
                            "content": "Hello CodeForge!",
                            "timestamp": "2026-07-06T12:00:00Z"
                        },
                        {
                            "role": "assistant",
                            "content": "Hello! How can I assist you in coding today?",
                            "timestamp": "2026-07-06T12:00:02Z"
                        }
                    ]
                }
            }
        }
    }
)
async def get_history(
    service: ChatService = Depends(get_chat_service)
):
    return await service.get_chat_history()

@router.delete(
    "/history",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear conversation history",
    description="Permanently delete conversation logs from memory while preserving other categories (such as plans or tool logs).",
    responses={
        204: {
            "description": "Conversation history successfully cleared"
        }
    }
)
async def clear_history(
    service: ChatService = Depends(get_chat_service)
):
    await service.clear_chat_history()
    return None
