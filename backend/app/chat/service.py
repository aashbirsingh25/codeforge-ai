import time
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timezone

from app.llm.factory import ProviderFactory
from app.llm.schemas import ChatCompletionRequest, ChatMessage as LLMChatMessage
from app.llm.exceptions import LLMException
from app.memory.manager import MemoryManager
from app.memory.schemas import MemoryEntry
from app.core.config import settings
from app.chat.schemas import ChatResponse, ChatHistoryMessage
from app.chat.exceptions import ChatProviderException

logger = logging.getLogger("app.chat.service")

class ChatService:
    def __init__(self, manager: Optional[MemoryManager] = None, user_id: Optional[str] = None):
        self.manager = manager or MemoryManager()
        self.user_id = user_id or "default"

    async def get_chat_history(self, limit: int = 50) -> List[ChatHistoryMessage]:
        try:
            entries = self.manager.retrieve_by_category("conversation", limit=limit)
            # Reverse list to keep chronological order (oldest message first)
            entries.reverse()
            
            history = []
            for entry in entries:
                role = entry.metadata.get("role", "user")
                history.append(ChatHistoryMessage(
                    role=role,
                    content=entry.content,
                    timestamp=entry.timestamp.isoformat()
                ))
            return history
        except Exception as e:
            logger.error(f"Failed to retrieve chat history from memory: {e}")
            return []

    async def clear_chat_history(self) -> None:
        try:
            entries = self.manager.store.list(category="conversation")
            for entry in entries:
                self.manager.store.delete(entry.id)
        except Exception as e:
            logger.error(f"Failed to clear chat history: {e}")

    async def send_message(self, user_message: str) -> ChatResponse:
        start_time = time.perf_counter()
        
        # 1. Save user message to memory
        try:
            self.manager.save_conversation(
                conversation_id=self.user_id,
                message=user_message,
                role="user"
            )
        except Exception as e:
            logger.warning(f"Failed to save user message to memory: {e}")

        # 2. Retrieve relevant context blocks using Memory Engine search queries
        context_blocks = []
        
        try:
            # Query similar plan history
            plans = self.manager.retrieve_similar(query=user_message, limit=2, category="plan")
            if plans:
                context_blocks.append("--- RELEVANT PLANNING HISTORY ---")
                for p in plans:
                    goal = p.metadata.get("goal", "Unknown Goal")
                    context_blocks.append(f"Plan Goal: '{goal}'\nPlan Content: {p.content}")
                    
            # Query similar execution history
            executions = self.manager.retrieve_similar(query=user_message, limit=2, category="execution")
            if executions:
                context_blocks.append("--- RECENT EXECUTION HISTORY ---")
                for ex in executions:
                    context_blocks.append(f"Execution: {ex.content}")
                    
            # Query similar tool execution history
            tools = self.manager.retrieve_similar(query=user_message, limit=3, category="tool_output")
            if tools:
                context_blocks.append("--- RELEVANT TOOL EXECUTION HISTORY ---")
                for t in tools:
                    context_blocks.append(f"Tool {t.metadata.get('tool_name')}: {t.content}")
        except Exception as e:
            logger.warning(f"Failed to retrieve context from Memory Engine: {e}")

        # 3. Retrieve recent conversation message history
        history_messages = await self.get_chat_history(limit=10)
        
        # Build prompt context blocks
        context_str = "\n\n".join(context_blocks)
        system_instruction = (
            "You are a helpful Software Engineering Assistant in the CodeForge AI platform.\n"
            "Answer the user's questions clearly, concisely, and correctly.\n"
        )
        if context_str:
            system_instruction += (
                f"\nHere is some relevant context from memory to help answer the user request:\n{context_str}\n"
            )

        # 4. Resolve LLM provider & settings
        provider_name = settings.LLM_PROVIDER
        try:
            provider = ProviderFactory.get_provider(provider_name)
        except ValueError as e:
            raise ChatProviderException(f"Failed to load provider: {str(e)}") from e

        if provider_name == "gemini":
            model_name = settings.GEMINI_MODEL
        elif provider_name == "openai":
            model_name = settings.OPENAI_MODEL
        else:
            model_name = settings.GEMINI_MODEL

        # 5. Build LLM Chat completion messages
        messages = [LLMChatMessage(role="system", content=system_instruction)]
        
        # Add conversation history
        for msg in history_messages:
            messages.append(LLMChatMessage(role=msg.role, content=msg.content))
        
        # Fallback safeguard in case history retrieval was empty
        if not any(m.content == user_message for m in history_messages):
            messages.append(LLMChatMessage(role="user", content=user_message))

        chat_request = ChatCompletionRequest(
            model=model_name,
            messages=messages
        )

        # 6. Request completion from LLM provider
        try:
            chat_response = await provider.generate(chat_request)
            assistant_response = chat_response.content
        except LLMException as e:
            logger.error(f"LLM Chat completions failed: provider={provider_name} error={type(e).__name__}")
            raise ChatProviderException(f"LLM Provider failure: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unhandled LLM Chat completions failure: provider={provider_name} error={type(e).__name__}")
            raise ChatProviderException(f"Chat failed: {str(e)}") from e

        # 7. Save assistant reply to memory
        try:
            self.manager.save_conversation(
                conversation_id=self.user_id,
                message=assistant_response,
                role="assistant"
            )
        except Exception as e:
            logger.warning(f"Failed to save assistant response to memory: {e}")

        duration = time.perf_counter() - start_time
        
        return ChatResponse(
            response=assistant_response,
            provider=provider_name,
            duration_seconds=duration
        )

    async def send_message_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        logger.info("Starting message stream processing")
        # 1. Save user message to memory
        try:
            self.manager.save_conversation(
                conversation_id=self.user_id,
                message=user_message,
                role="user"
            )
        except Exception as e:
            logger.warning(f"Failed to save user message to memory: {e}")

        # 2. Retrieve relevant context blocks using Memory Engine search queries
        context_blocks = []
        try:
            plans = self.manager.retrieve_similar(query=user_message, limit=2, category="plan")
            if plans:
                context_blocks.append("--- RELEVANT PLANNING HISTORY ---")
                for p in plans:
                    context_blocks.append(f"Plan Goal: '{p.metadata.get('goal')}'\nPlan Content: {p.content}")
            executions = self.manager.retrieve_similar(query=user_message, limit=2, category="execution")
            if executions:
                context_blocks.append("--- RECENT EXECUTION HISTORY ---")
                for ex in executions:
                    context_blocks.append(f"Execution: {ex.content}")
            tools = self.manager.retrieve_similar(query=user_message, limit=3, category="tool_output")
            if tools:
                context_blocks.append("--- RELEVANT TOOL EXECUTION HISTORY ---")
                for t in tools:
                    context_blocks.append(f"Tool {t.metadata.get('tool_name')}: {t.content}")
        except Exception as e:
            logger.warning(f"Failed to retrieve context from Memory Engine: {e}")

        # 3. Retrieve recent conversation message history
        history_messages = await self.get_chat_history(limit=10)
        
        # Build prompt context blocks
        context_str = "\n\n".join(context_blocks)
        system_instruction = (
            "You are a helpful Software Engineering Assistant in the CodeForge AI platform.\n"
            "Answer the user's questions clearly, concisely, and correctly.\n"
        )
        if context_str:
            system_instruction += (
                f"\nHere is some relevant context from memory to help answer the user request:\n{context_str}\n"
            )

        # 4. Resolve LLM provider & settings
        provider_name = settings.LLM_PROVIDER
        try:
            provider = ProviderFactory.get_provider(provider_name)
        except ValueError as e:
            raise ChatProviderException(f"Failed to load provider: {str(e)}") from e

        if provider_name == "gemini":
            model_name = settings.GEMINI_MODEL
        elif provider_name == "openai":
            model_name = settings.OPENAI_MODEL
        else:
            model_name = settings.GEMINI_MODEL

        # 5. Build LLM Chat completion messages
        messages = [LLMChatMessage(role="system", content=system_instruction)]
        for msg in history_messages:
            messages.append(LLMChatMessage(role=msg.role, content=msg.content))
        if not any(m.content == user_message for m in history_messages):
            messages.append(LLMChatMessage(role="user", content=user_message))

        chat_request = ChatCompletionRequest(
            model=model_name,
            messages=messages
        )

        # 6. Stream completion from LLM provider
        import json
        full_response = []
        try:
            yield f"event: started\ndata: {json.dumps({'status': 'started'})}\n\n"
            
            async for chunk in provider.generate_stream(chat_request):
                full_response.append(chunk)
                yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
                
            assistant_response = "".join(full_response)
            
            # 7. Save assistant reply to memory
            try:
                self.manager.save_conversation(
                    conversation_id=self.user_id,
                    message=assistant_response,
                    role="assistant"
                )
            except Exception as e:
                logger.warning(f"Failed to save assistant response to memory: {e}")
                
            yield f"event: completed\ndata: {json.dumps({'response': assistant_response, 'provider': provider_name})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream generation failed: {e}")
            code = "INTERNAL_ERROR"
            status_code = 500
            
            # Extract structured status_code or error code if it's a known LLMException
            if isinstance(e, LLMException):
                status_code = getattr(e, "status_code", 500)
                if status_code == 429:
                    code = "QUOTA_EXHAUSTED"
                elif status_code == 401:
                    code = "AUTHENTICATION_FAILED"
                elif status_code == 503:
                    code = "PROVIDER_UNAVAILABLE"
                elif status_code == 504:
                    code = "TIMEOUT"
                else:
                    code = "BAD_REQUEST"
            
            yield f"event: failed\ndata: {json.dumps({'error': str(e), 'code': code, 'status_code': status_code})}\n\n"
