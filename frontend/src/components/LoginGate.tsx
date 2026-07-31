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
  Link,
  CircularProgress,
} from '@mui/material';
import { Mail, Lock, Eye, EyeOff, Code2, UserPlus, LogIn } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const LoginGate: React.FC = () => {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const { login, signup, error, setError } = useAuth();

  const handleToggleMode = () => {
    setMode((prev) => (prev === 'login' ? 'signup' : 'login'));
    setLocalError(null);
    setError(null);
    setPassword('');
    setConfirmPassword('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    setError(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setLocalError('Please enter a valid email address.');
      return;
    }

    if (!password) {
      setLocalError('Please enter your password.');
      return;
    }

    if (mode === 'signup') {
      if (password.length < 8) {
        setLocalError('Password must be at least 8 characters long.');
        return;
      }
      if (password !== confirmPassword) {
        setLocalError('Passwords do not match.');
        return;
      }
    }

    setLoading(true);
    try {
      if (mode === 'login') {
        await login(trimmedEmail, password);
      } else {
        await signup(trimmedEmail, password);
      }
    } catch (err: any) {
      // Error handled by AuthContext
    } finally {
      setLoading(false);
    }
  };

  const activeError = localError || error;

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
              {mode === 'login' ? 'Sign in to access your workspace' : 'Create an account to get started'}
            </Typography>
          </Box>

          {activeError && (
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
              {activeError}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              variant="outlined"
              type="email"
              label="Email Address"
              placeholder="user@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <Mail size={20} color="#94a3b8" />
                    </InputAdornment>
                  ),
                },
              }}
              sx={{
                mb: 2.5,
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

            <TextField
              fullWidth
              variant="outlined"
              type={showPassword ? 'text' : 'password'}
              label="Password"
              placeholder="Enter password..."
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <Lock size={20} color="#94a3b8" />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                        sx={{ color: '#94a3b8' }}
                      >
                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                      </IconButton>
                    </InputAdornment>
                  ),
                },
              }}
              sx={{
                mb: mode === 'signup' ? 2.5 : 3,
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

            {mode === 'signup' && (
              <TextField
                fullWidth
                variant="outlined"
                type={showPassword ? 'text' : 'password'}
                label="Confirm Password"
                placeholder="Confirm password..."
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                slotProps={{
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <Lock size={20} color="#94a3b8" />
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
            )}

            <Button
              fullWidth
              type="submit"
              variant="contained"
              disabled={loading || !email.trim() || !password}
              startIcon={
                loading ? (
                  <CircularProgress size={18} color="inherit" />
                ) : mode === 'login' ? (
                  <LogIn size={18} />
                ) : (
                  <UserPlus size={18} />
                )
              }
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
              {loading ? 'Processing...' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </Button>

            <Box sx={{ mt: 3, textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#94a3b8' }}>
                {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
                <Link
                  component="button"
                  type="button"
                  onClick={handleToggleMode}
                  sx={{
                    color: '#00f2fe',
                    fontWeight: 600,
                    textDecoration: 'none',
                    '&:hover': { textDecoration: 'underline' },
                  }}
                >
                  {mode === 'login' ? 'Sign Up' : 'Log In'}
                </Link>
              </Typography>
            </Box>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
};

export default LoginGate;
