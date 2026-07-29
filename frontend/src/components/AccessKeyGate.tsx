import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  InputAdornment,
  IconButton,
} from '@mui/material';
import { KeyRound, Lock, Eye, EyeOff, Code2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const AccessKeyGate: React.FC = () => {
  const [inputKey, setInputKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const { submitKey, error } = useAuth();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputKey.trim()) {
      submitKey(inputKey);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100vw',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#090d16',
        backgroundImage: 'radial-gradient(ellipse at 50% 30%, rgba(0, 242, 254, 0.08), transparent 70%)',
        p: 2,
      }}
    >
      <Card
        sx={{
          maxWidth: 440,
          width: '100%',
          backgroundColor: 'rgba(17, 23, 38, 0.85)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(36, 48, 79, 0.8)',
          borderRadius: 4,
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5), 0 0 30px rgba(0, 242, 254, 0.1)',
          overflow: 'hidden',
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 3 }}>
            <Box
              sx={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, rgba(0, 242, 254, 0.2), rgba(168, 85, 247, 0.2))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mb: 2,
                border: '1px solid rgba(0, 242, 254, 0.3)',
              }}
            >
              <Code2 size={32} color="#00f2fe" />
            </Box>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#f8fafc', textAlign: 'center' }}>
              CodeForge AI
            </Typography>
            <Typography variant="body2" sx={{ color: '#94a3b8', mt: 0.5, textAlign: 'center' }}>
              Enter your access key to unlock the application
            </Typography>
          </Box>

          {error && (
            <Alert
              severity="error"
              variant="filled"
              sx={{
                mb: 3,
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                color: '#f87171',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: 2,
              }}
            >
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              variant="outlined"
              type={showKey ? 'text' : 'password'}
              label="Access Key"
              placeholder="Enter API Secret Key..."
              value={inputKey}
              onChange={(e) => setInputKey(e.target.value)}
              autoFocus
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <KeyRound size={20} color="#94a3b8" />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowKey(!showKey)}
                        edge="end"
                        sx={{ color: '#94a3b8' }}
                      >
                        {showKey ? <EyeOff size={18} /> : <Eye size={18} />}
                      </IconButton>
                    </InputAdornment>
                  ),
                },
              }}
              sx={{
                mb: 3,
                '& .MuiOutlinedInput-root': {
                  backgroundColor: 'rgba(9, 13, 22, 0.6)',
                  borderRadius: 2,
                  '& fieldset': {
                    borderColor: 'rgba(36, 48, 79, 0.8)',
                  },
                  '&:hover fieldset': {
                    borderColor: '#00f2fe',
                  },
                  '&.Mui-focused fieldset': {
                    borderColor: '#00f2fe',
                  },
                },
                '& .MuiInputLabel-root': {
                  color: '#94a3b8',
                  '&.Mui-focused': {
                    color: '#00f2fe',
                  },
                },
              }}
            />

            <Button
              fullWidth
              type="submit"
              variant="contained"
              disabled={!inputKey.trim()}
              startIcon={<Lock size={18} />}
              sx={{
                py: 1.5,
                borderRadius: 2,
                background: 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)',
                color: '#090d16',
                fontWeight: 700,
                fontSize: '1rem',
                textTransform: 'none',
                boxShadow: '0 4px 14px rgba(0, 242, 254, 0.3)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                  boxShadow: '0 6px 20px rgba(0, 242, 254, 0.4)',
                },
                '&.Mui-disabled': {
                  background: 'rgba(36, 48, 79, 0.5)',
                  color: '#64748b',
                },
              }}
            >
              Unlock Access
            </Button>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
};

export default AccessKeyGate;
