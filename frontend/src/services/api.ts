import axios from 'axios';

// In-memory key storage (never written to localStorage/sessionStorage)
let currentApiKey: string | null = null;

export const setApiKey = (key: string | null) => {
  currentApiKey = key;
};

export const getApiKey = (): string | null => currentApiKey;

// Determine API base URL dynamically from environment (Vercel build-time env var) or default to relative path
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Create central Axios instance targeting the v1 API prefix
export const api = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach X-API-Key header to every outgoing request if available
api.interceptors.request.use((config) => {
  if (currentApiKey) {
    config.headers['X-API-Key'] = currentApiKey;
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
      setApiKey(null);
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
