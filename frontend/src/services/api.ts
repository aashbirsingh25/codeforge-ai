import axios from 'axios';

// Create central Axios instance targeting the v1 API prefix
export const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
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

// Response Interceptor for global error catching
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ')
        : error.response?.data?.message || error.message || 'A network error occurred';
    
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
