import { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  TextField,
  IconButton,
  Button,
  Paper,
  CircularProgress,
  Avatar,
  Stack,
  Alert,
} from '@mui/material';
import {
  Send as SendIcon,
  DeleteSweep as DeleteSweepIcon,
  SmartToy as RobotIcon,
  Person as UserIcon,
} from '@mui/icons-material';
import { chatService, ChatHistoryMessage, ChatStreamError } from '../services/chatService';

export default function Chat() {
  const [messages, setMessages] = useState<ChatHistoryMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chat history on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const history = await chatService.getHistory();
        setMessages(history);
      } catch (err) {
        console.error('Failed to load chat history', err);
      }
    };
    loadHistory();
  }, []);

  // Auto-scroll to bottom when messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || loading) return;

    const userQuery = inputValue;
    setInputValue('');
    setLoading(true);
    setStreamingMessage('');
    setErrorMessage(null);

    // Append user message immediately
    const userMsg: ChatHistoryMessage = {
      role: 'user',
      content: userQuery,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Stream the assistant response
    let accumulatedText = '';
    await chatService.streamMessage(
      userQuery,
      (chunk) => {
        accumulatedText += chunk;
        setStreamingMessage(accumulatedText);
      },
      (error) => {
        console.error('Streaming error:', error);
        if (error instanceof ChatStreamError && error.code === 'QUOTA_EXHAUSTED') {
          setErrorMessage('Gemini free-tier quota has been exhausted. Please wait for the quota to reset, switch models, or configure another provider.');
        } else {
          setErrorMessage(error.message || 'An unexpected error occurred while streaming response.');
        }
        setLoading(false);
      }
    );

    // Finalize: append assistant response to message list
    if (accumulatedText) {
      const assistantMsg: ChatHistoryMessage = {
        role: 'assistant',
        content: accumulatedText,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    }
    
    setStreamingMessage('');
    setLoading(false);
  };

  const handleClearHistory = async () => {
    if (window.confirm('Are you sure you want to clear your conversation history?')) {
      try {
        await chatService.clearHistory();
        setMessages([]);
      } catch (err) {
        console.error('Failed to clear history', err);
      }
    }
  };

  // Helper to parse ``` codeblocks ``` in message content
  const renderMessageContent = (content: string) => {
    const parts = content.split(/(```[\s\S]*?```)/g);
    return parts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        const lines = part.slice(3, -3).split('\n');
        let language = 'code';
        let codeLines = lines;
        if (lines[0] && !lines[0].includes(' ') && lines[0].length < 15) {
          language = lines[0];
          codeLines = lines.slice(1);
        }
        const code = codeLines.join('\n').trim();
        return (
          <Box
            key={index}
            sx={{
              fontFamily: 'Fira Code, monospace',
              fontSize: '0.85rem',
              bgcolor: 'brand.code',
              p: 2,
              borderRadius: '8px',
              border: '1px solid #24304f',
              my: 1.5,
              whiteSpace: 'pre-wrap',
              overflowX: 'auto',
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="caption" sx={{ color: 'text.disabled', fontWeight: 600 }}>
                {language.toUpperCase()}
              </Typography>
            </Box>
            <code>{code}</code>
          </Box>
        );
      }
      return (
        <Typography key={index} variant="body1" sx={{ whiteSpace: 'pre-line', lineHeight: 1.6 }}>
          {part}
        </Typography>
      );
    });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 128px)', gap: 2 }}>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #24304f', pb: 2.5 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: 'text.primary' }}>
            AI Chat Assistant
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
            Interactive coding assistant connected directly to the CodeForge workspace.
          </Typography>
        </Box>
        {messages.length > 0 && (
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteSweepIcon />}
            onClick={handleClearHistory}
            sx={{
              borderColor: 'error.main',
              bgcolor: 'rgba(239, 68, 68, 0.05)',
              '&:hover': {
                bgcolor: 'rgba(239, 68, 68, 0.15)',
              },
            }}
          >
            Clear History
          </Button>
        )}
      </Box>

      {/* Messages Scroll Area */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          pr: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: 3,
        }}
      >
        {messages.length === 0 && !loading && (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 2, textAlign: 'center', px: 4 }}>
            <RobotIcon sx={{ fontSize: 60, color: 'text.disabled' }} />
            <Typography variant="h6" sx={{ color: 'text.primary', fontWeight: 600 }}>
              How can I help you build today?
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 450 }}>
              Ask a question, request code templates, or query previous execution plans. I have full read access to your local workspace.
            </Typography>
          </Box>
        )}

        {/* Chronological Message bubbles */}
        {messages.map((msg, index) => {
          const isUser = msg.role === 'user';
          return (
            <Stack
              key={index}
              direction="row"
              spacing={2}
              sx={{ width: '100%', justifyContent: isUser ? 'flex-end' : 'flex-start' }}
            >
              {!isUser && (
                <Avatar sx={{ bgcolor: 'accent.purple', width: 36, height: 36 }}>
                  <RobotIcon fontSize="small" />
                </Avatar>
              )}
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  maxWidth: '75%',
                  borderRadius: '12px',
                  bgcolor: isUser ? 'brand.card' : 'brand.panel',
                  borderColor: isUser ? 'accent.primary' : '#24304f',
                  boxShadow: isUser ? '0 2px 10px rgba(0, 242, 254, 0.05)' : 'none',
                }}
              >
                {renderMessageContent(msg.content)}
              </Paper>
              {isUser && (
                <Avatar sx={{ bgcolor: 'accent.primary', width: 36, height: 36, color: 'brand.bg' }}>
                  <UserIcon fontSize="small" />
                </Avatar>
              )}
            </Stack>
          );
        })}

        {/* Live streaming message bubble */}
        {streamingMessage && (
          <Stack direction="row" spacing={2} sx={{ width: '100%', justifyContent: 'flex-start' }}>
            <Avatar sx={{ bgcolor: 'accent.purple', width: 36, height: 36 }}>
              <RobotIcon fontSize="small" />
            </Avatar>
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                maxWidth: '75%',
                borderRadius: '12px',
                bgcolor: 'brand.panel',
                borderColor: '#24304f',
              }}
            >
              {renderMessageContent(streamingMessage)}
            </Paper>
          </Stack>
        )}

        {/* Loading / Waiting for first token */}
        {loading && !streamingMessage && (
          <Stack direction="row" spacing={2} sx={{ width: '100%', justifyContent: 'flex-start' }}>
            <Avatar sx={{ bgcolor: 'accent.purple', width: 36, height: 36 }}>
              <RobotIcon fontSize="small" />
            </Avatar>
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                borderRadius: '12px',
                bgcolor: 'brand.panel',
                borderColor: '#24304f',
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
              }}
            >
              <CircularProgress size={16} sx={{ color: 'accent.purple' }} />
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                CodeForge is thinking...
              </Typography>
            </Paper>
          </Stack>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {errorMessage && (
        <Alert
          severity="error"
          onClose={() => setErrorMessage(null)}
          sx={{
            borderRadius: '8px',
            bgcolor: 'rgba(239, 68, 68, 0.1)',
            color: 'rgb(252, 165, 165)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            '& .MuiAlert-icon': {
              color: 'rgb(248, 113, 113)',
            },
          }}
        >
          {errorMessage}
        </Alert>
      )}

      {/* Message input panel */}
      <Box
        component="form"
        onSubmit={handleSend}
        sx={{
          borderTop: '1px solid #24304f',
          pt: 2,
          display: 'flex',
          gap: 1.5,
        }}
      >
        <TextField
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Ask a question or enter a workspace instruction..."
          fullWidth
          disabled={loading}
          autoComplete="off"
          sx={{
            '& .MuiOutlinedInput-root': {
              bgcolor: 'brand.panel',
              borderRadius: '8px',
              '& fieldset': { borderColor: '#24304f' },
              '&:hover fieldset': { borderColor: 'accent.primary' },
              '&.Mui-focused fieldset': { borderColor: 'accent.primary' },
            },
          }}
        />
        <IconButton
          type="submit"
          disabled={!inputValue.trim() || loading}
          sx={{
            bgcolor: inputValue.trim() ? 'accent.primary' : 'brand.panel',
            color: inputValue.trim() ? 'brand.bg' : 'text.disabled',
            '&:hover': {
              bgcolor: 'accent.secondary',
            },
            borderRadius: '8px',
            p: 1.5,
            width: 52,
            height: 52,
            transition: 'all 0.2s',
          }}
        >
          <SendIcon />
        </IconButton>
      </Box>
    </Box>
  );
}
