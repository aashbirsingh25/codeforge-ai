import { api } from './api';

export interface ChatHistoryMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatResponse {
  response: string;
  provider: string;
  duration_seconds: number;
}

export class ChatStreamError extends Error {
  code?: string;
  statusCode?: number;

  constructor(message: string, code?: string, statusCode?: number) {
    super(message);
    this.name = 'ChatStreamError';
    this.code = code;
    this.statusCode = statusCode;
    Object.setPrototypeOf(this, ChatStreamError.prototype);
  }
}

export const chatService = {
  // Direct (non-streaming) message sending
  sendMessage: async (message: string): Promise<ChatResponse> => {
    const res = await api.post<ChatResponse>('/chat', { message });
    return res.data;
  },

  // Get chronological history log
  getHistory: async (): Promise<ChatHistoryMessage[]> => {
    const res = await api.get<ChatHistoryMessage[]>('/chat/history');
    return res.data;
  },

  // Clear conversation history
  clearHistory: async (): Promise<void> => {
    await api.delete('/chat/history');
  },

  // SSE Stream response using standard browser fetch + reader
  streamMessage: async (
    message: string,
    onChunk: (text: string) => void,
    onError: (err: any) => void
  ): Promise<void> => {
    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        const errText = await response.text().catch(() => 'Failed to initialize stream');
        throw new Error(errText || 'Streaming error');
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Readable stream not supported by browser.');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent: string | null = null;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          
          // Keep the last partial line in the buffer
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) {
              currentEvent = null;
              continue;
            }

            if (trimmed.startsWith('event:')) {
              currentEvent = trimmed.slice(6).trim();
              continue;
            }

            if (trimmed.startsWith('data:')) {
              const dataStr = trimmed.slice(5).trim();
              
              // 1. Separate JSON parsing
              let parsedData: any = null;
              let isJson = false;
              try {
                parsedData = JSON.parse(dataStr);
                isJson = true;
              } catch (e) {
                // Not valid JSON
              }

              // 2. Separate runtime error handling and processing
              if (isJson) {
                if (currentEvent === 'failed' || (parsedData && typeof parsedData === 'object' && 'error' in parsedData)) {
                  const errMsg = parsedData.error || 'Streaming error';
                  const errCode = parsedData.code;
                  const errStatus = parsedData.status_code;
                  throw new ChatStreamError(errMsg, errCode, errStatus);
                }

                if (parsedData && typeof parsedData === 'object') {
                  if ('token' in parsedData) {
                    onChunk(parsedData.token);
                  } else if ('content' in parsedData) {
                    onChunk(parsedData.content);
                  }
                } else if (typeof parsedData === 'string') {
                  onChunk(parsedData);
                }
              } else {
                // Fallback to literal chunk extraction
                onChunk(dataStr);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (err) {
      onError(err);
    }
  },
};
