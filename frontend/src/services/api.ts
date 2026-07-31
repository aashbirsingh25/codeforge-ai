import axios from 'axios';

// In-memory token storage (never written to localStorage/sessionStorage)
let currentAccessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  currentAccessToken = token;
};

export const getAccessToken = (): string | null => currentAccessToken;

// Determine API base URL dynamically from environment or default to relative path
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Create central Axios instance targeting the v1 API prefix
export const api = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach Authorization Bearer header to every outgoing request if available
api.interceptors.request.use((config) => {
  if (currentAccessToken) {
    config.headers['Authorization'] = `Bearer ${currentAccessToken}`;
  }
  return config;
});

// Listener pattern for global error toasts
type ErrorListener = (message: string) => void;
const errorListeners = new Set<ErrorListener>();

export const subscribeToErrors = (listener: ErrorListener) => {
  errorListeners.add(listener);
  return () => {
    errorListeners.delete(listener);
  };
};

export const notifyError = (message: string) => {
  errorListeners.forEach((listener) => listener(message));
};

// Listener pattern for 401 Unauthorized responses
type UnauthorizedListener = () => void;
const unauthorizedListeners = new Set<UnauthorizedListener>();

export const subscribeToUnauthorized = (listener: UnauthorizedListener) => {
  unauthorizedListeners.add(listener);
  return () => {
    unauthorizedListeners.delete(listener);
  };
};

const notifyUnauthorized = () => {
  unauthorizedListeners.forEach((listener) => listener());
};

// Response Interceptor for global error catching & 401 authorization state clearance
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      setAccessToken(null);
      notifyUnauthorized();
    }

    const detail = error.response?.data?.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ')
        : error.response?.data?.error?.message || error.response?.data?.message || error.message || 'A network error occurred';
    
    notifyError(message);
    return Promise.reject(error);
  }
);

// Auth API endpoints
export interface UserPayload {
  id: string;
  email: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserPayload;
}

export const loginApi = async (email: string, password: string): Promise<AuthResponse> => {
  const res = await api.post<AuthResponse>('/auth/login', { email, password });
  return res.data;
};

export const signupApi = async (email: string, password: string): Promise<AuthResponse> => {
  const res = await api.post<AuthResponse>('/auth/signup', { email, password });
  return res.data;
};

// Shared Schemas
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface Project {
  id: string;
  name: string;
  path: string;
  status: string;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  status: string;
}
