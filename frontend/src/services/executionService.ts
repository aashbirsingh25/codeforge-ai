import { api } from './api';
import { Agent } from './api';

export interface PlanningRequest {
  goal: string;
  strategy?: string;
  provider?: string;
}

export interface SubTask {
  id: string;
  title: string;
  description: string;
  status: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  priority: string;
  estimated_complexity: string;
  estimated_duration: string;
  dependencies: string[];
  status: string;
  subtasks: SubTask[];
}

export interface ExecutionPlan {
  goal: string;
  tasks: Task[];
}

export interface PlanningResponse {
  plan: ExecutionPlan;
  strategy: string;
  provider: string;
  duration_seconds: number;
}

export interface ExecutionRequest {
  goal?: string;
  plan?: ExecutionPlan;
}

export interface AgentAction {
  tool_name: string;
  tool_args: Record<string, any>;
  description?: string;
}

export interface AgentObservation {
  content: string;
  success: boolean;
  error?: string;
}

export interface ExecutionStep {
  task_id: string;
  status: string;
  actions: AgentAction[];
  observations: AgentObservation[];
  retry_count: number;
  error?: string;
  start_time?: string;
  end_time?: string;
}

export interface ExecutionState {
  current_task?: string;
  completed_tasks: string[];
  failed_tasks: string[];
  pending_tasks: string[];
  observations: Record<string, AgentObservation[]>;
  execution_history: ExecutionStep[];
  timestamps: Record<string, any>;
  retry_count: Record<string, number>;
}

export interface ExecutionMetrics {
  start_time: string;
  end_time?: string;
  duration_seconds?: number;
  retry_count: number;
}

export interface Thought {
  reasoning: string;
}

export interface Action {
  tool_name: string;
  tool_args: Record<string, any>;
}

export interface Observation {
  content: string;
  success: boolean;
  error?: string;
}

export interface ReActStep {
  thought: Thought;
  action?: Action;
  observation?: Observation;
  duration_seconds: number;
}

export interface ReActTrace {
  execution_id: string;
  steps: ReActStep[];
}

export interface ExecutionResponse {
  execution_id: string;
  status: string;
  plan: ExecutionPlan;
  state: ExecutionState;
  metrics: ExecutionMetrics;
  react_trace?: ReActTrace;
}

export const executionService = {
  // Get registered agent list
  listAgents: async (): Promise<{ agents: Agent[] }> => {
    const res = await api.get<{ agents: Agent[] }>('/agents');
    return res.data;
  },

  // Get available planning strategies
  getStrategies: async (): Promise<string[]> => {
    const res = await api.get<string[]>('/planner/strategies');
    return res.data;
  },

  // Generate an execution plan from a goal
  generatePlan: async (req: PlanningRequest): Promise<PlanningResponse> => {
    const res = await api.post<PlanningResponse>('/planner/plan', req);
    return res.data;
  },

  // Execute a goal or plan
  execute: async (req: ExecutionRequest): Promise<ExecutionResponse> => {
    const res = await api.post<ExecutionResponse>('/agents/execute', req);
    return res.data;
  },

  // Execute an existing plan directly
  executePlan: async (plan: ExecutionPlan): Promise<ExecutionResponse> => {
    const res = await api.post<ExecutionResponse>('/agents/execute/plan', plan);
    return res.data;
  },

  // Get current or latest execution status
  getStatus: async (executionId?: string): Promise<ExecutionResponse> => {
    const params = executionId ? { execution_id: executionId } : {};
    const res = await api.get<ExecutionResponse>('/agents/status', { params });
    return res.data;
  },

  // Get history of execution runs
  getHistory: async (): Promise<ExecutionResponse[]> => {
    const res = await api.get<ExecutionResponse[]>('/agents/history');
    return res.data;
  },

  // Get trace detail for a specific execution
  getTrace: async (executionId: string): Promise<ReActTrace> => {
    const res = await api.get<ReActTrace>(`/agents/${executionId}/trace`);
    return res.data;
  },

  // Cancel running execution
  cancel: async (executionId: string): Promise<{ message: string }> => {
    const res = await api.post<{ message: string }>(`/agents/${executionId}/cancel`);
    return res.data;
  },

  // SSE Stream execution events
  streamEvents: (
    executionId: string,
    onEvent: (event: { type: string; data: any }) => void,
    onError: (err: any) => void
  ): (() => void) => {
    const eventSource = new EventSource(`/api/v1/agents/${executionId}/events`);

    const handleEvent = (type: string) => (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        onEvent({ type, data });
      } catch (err) {
        onEvent({ type, data: e.data });
      }
    };

    // Standard event types emitted by execution engine
    const eventTypes = [
      'planning',
      'started',
      'thinking',
      'tool_call',
      'tool_result',
      'observation',
      'completed',
      'failed',
      'cancelled',
    ];

    eventTypes.forEach((type) => {
      eventSource.addEventListener(type, handleEvent(type));
    });

    eventSource.onerror = (e) => {
      onError(e);
    };

    return () => {
      eventSource.close();
    };
  },
};
