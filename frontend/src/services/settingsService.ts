import { api } from './api';

export interface SystemSettings {
  project_name: string;
  api_v1_str: string;
  workspace_dir: string;
}

export interface ProviderInfo {
  name: string;
  available_models: string[];
  is_configured: boolean;
}

export interface ProviderHealthResponse {
  provider: string;
  status: 'healthy' | 'unhealthy';
  error_message?: string;
}

export const settingsService = {
  // Get main system config options
  getSettings: async (): Promise<SystemSettings> => {
    const res = await api.get<SystemSettings>('/settings');
    return res.data;
  },

  // Save/Update configurations
  updateSettings: async (): Promise<{ status: string }> => {
    const res = await api.post<{ status: string }>('/settings');
    return res.data;
  },

  // List providers info and supported models
  getProviders: async (): Promise<ProviderInfo[]> => {
    const res = await api.get<ProviderInfo[]>('/settings/providers');
    return res.data;
  },

  // Run health check checks for Gemini / OpenAI
  checkProvidersHealth: async (): Promise<ProviderHealthResponse[]> => {
    const res = await api.get<ProviderHealthResponse[]>('/settings/providers/health');
    return res.data;
  },
};
