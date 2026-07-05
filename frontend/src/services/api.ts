const BASE_URL = '/api/v1';

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

export interface MemorySummary {
  short_term_contexts_count: number;
  long_term_vector_nodes: number;
  status: string;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error('Network error fetching health status');
  return res.json();
}

export async function fetchProjects(): Promise<{ projects: Project[] }> {
  const res = await fetch(`${BASE_URL}/projects`);
  if (!res.ok) throw new Error('Network error fetching projects registry');
  return res.json();
}

export async function fetchAgents(): Promise<{ agents: Agent[] }> {
  const res = await fetch(`${BASE_URL}/agents`);
  if (!res.ok) throw new Error('Network error fetching sub-agents configurations');
  return res.json();
}

export async function fetchMemory(): Promise<MemorySummary> {
  const res = await fetch(`${BASE_URL}/memory`);
  if (!res.ok) throw new Error('Network error fetching memory allocations');
  return res.json();
}
