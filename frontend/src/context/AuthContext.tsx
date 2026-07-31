import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  setAccessToken,
  getAccessToken,
  subscribeToUnauthorized,
  loginApi,
  signupApi,
  UserPayload
} from '../services/api';

interface AuthContextType {
  accessToken: string | null;
  user: UserPayload | null;
  isAuthenticated: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setError: (msg: string | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [accessToken, setAccessTokenState] = useState<string | null>(getAccessToken());
  const [user, setUser] = useState<UserPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const login = async (email: string, password: string) => {
    try {
      const res = await loginApi(email, password);
      setAccessToken(res.access_token);
      setAccessTokenState(res.access_token);
      setUser(res.user);
      setError(null);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : 'Login failed. Please check your credentials.';
      setError(msg);
      throw new Error(msg);
    }
  };

  const signup = async (email: string, password: string) => {
    try {
      const res = await signupApi(email, password);
      setAccessToken(res.access_token);
      setAccessTokenState(res.access_token);
      setUser(res.user);
      setError(null);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ')
          : 'Signup failed. Please try again.';
      setError(msg);
      throw new Error(msg);
    }
  };

  const logout = () => {
    setAccessToken(null);
    setAccessTokenState(null);
    setUser(null);
    setError(null);
  };

  useEffect(() => {
    const unsubscribe = subscribeToUnauthorized(() => {
      setAccessToken(null);
      setAccessTokenState(null);
      setUser(null);
      setError('Session expired or unauthorized. Please log in again.');
    });
    return unsubscribe;
  }, []);

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        user,
        isAuthenticated: Boolean(accessToken),
        error,
        login,
        signup,
        logout,
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
