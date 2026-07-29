import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { setApiKey, getApiKey, subscribeToUnauthorized } from '../services/api';

interface AuthContextType {
  apiKey: string | null;
  isAuthenticated: boolean;
  error: string | null;
  submitKey: (key: string) => void;
  clearKey: () => void;
  setError: (msg: string | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [apiKey, setApiKeyState] = useState<string | null>(getApiKey());
  const [error, setError] = useState<string | null>(null);

  const submitKey = (key: string) => {
    const trimmed = key.trim();
    if (!trimmed) {
      setError('Please enter a valid access key.');
      return;
    }
    setApiKey(trimmed);
    setApiKeyState(trimmed);
    setError(null);
  };

  const clearKey = () => {
    setApiKey(null);
    setApiKeyState(null);
  };

  useEffect(() => {
    const unsubscribe = subscribeToUnauthorized(() => {
      setApiKeyState(null);
      setError('Incorrect key. Access denied.');
    });
    return unsubscribe;
  }, []);

  return (
    <AuthContext.Provider
      value={{
        apiKey,
        isAuthenticated: Boolean(apiKey),
        error,
        submitKey,
        clearKey,
        setError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
