import { api } from './api';

export interface TelemetryMetrics {
  uptime_seconds: number;
  active_executions: number;
  completed_executions: number;
  failed_executions: number;
  cancelled_executions: number;
  memory_usage_bytes: number;
  request_count: number;
  provider_usage: Record<string, number>;
  average_execution_duration_seconds: number;
}

export const metricsService = {
  // Get telemetry metrics from FastAPI backend
  getMetrics: async (): Promise<TelemetryMetrics> => {
    const res = await api.get<TelemetryMetrics>('/metrics');
    return res.data;
  },
};
