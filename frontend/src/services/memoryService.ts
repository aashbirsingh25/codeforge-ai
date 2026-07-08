import { api } from './api';

export interface MemoryEntry {
  id: string;
  timestamp: string;
  category: string;
  title: string;
  content: string;
  metadata: Record<string, any>;
  tags: string[];
}

export interface MemorySummary {
  total_entries: number;
  category_counts: Record<string, number>;
  recent_entries: MemoryEntry[];
}

export interface MemorySearchItem {
  entry: MemoryEntry;
  score: number;
}

export interface MemorySearchResponse {
  results: MemorySearchItem[];
}

export interface MemoryStatistics {
  total_entries: number;
  category_counts: Record<string, number>;
  tag_counts: Record<string, number>;
  storage_size_bytes: number;
  last_updated: string;
}

export const memoryService = {
  // Get memory summary info
  getSummary: async (): Promise<MemorySummary> => {
    const res = await api.get<MemorySummary>('/memory');
    return res.data;
  },

  // Get raw list of memory entries
  listEntries: async (category?: string, tags?: string[], limit?: number): Promise<MemoryEntry[]> => {
    const params: Record<string, any> = {};
    if (category) params.category = category;
    if (tags && tags.length > 0) params.tags = tags;
    if (limit) params.limit = limit;

    const res = await api.get<MemoryEntry[]>('/memory/list', { params });
    return res.data;
  },

  // Search memories with scoring
  search: async (query: string, category?: string, tags?: string[], limit: number = 10): Promise<MemorySearchResponse> => {
    const params: Record<string, any> = { query, limit };
    if (category) params.category = category;
    if (tags && tags.length > 0) params.tags = tags;

    const res = await api.get<MemorySearchResponse>('/memory/search', { params });
    return res.data;
  },

  // Get complete memory storage statistics
  getStatistics: async (): Promise<MemoryStatistics> => {
    const res = await api.get<MemoryStatistics>('/memory/statistics');
    return res.data;
  },

  // Wipe all memories
  clearMemory: async (): Promise<void> => {
    await api.delete('/memory');
  },
};
