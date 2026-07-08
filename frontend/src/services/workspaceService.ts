import { api } from './api';

export interface FilesListResponse {
  files: string[];
  tracking: Record<string, string[]>;
}

export interface FileReadResponse {
  path: string;
  content: string;
}

export interface FileWriteResponse {
  path: string;
  success: boolean;
  message: string;
}

export interface FileUpdateResponse {
  path: string;
  applied: boolean;
  message: string;
  diff?: string;
}

export interface ProjectCreateResponse {
  message: string;
}

export const workspaceService = {
  // List files recursively from a path in workspace
  listFiles: async (path: string = '.'): Promise<FilesListResponse> => {
    const res = await api.get<FilesListResponse>('/workspace/files', {
      params: { path },
    });
    return res.data;
  },

  // Read file contents
  readFile: async (path: string): Promise<FileReadResponse> => {
    const res = await api.get<FileReadResponse>('/workspace/file', {
      params: { path },
    });
    return res.data;
  },

  // Create a new file in workspace
  createFile: async (path: string, content: string, overwrite: boolean = false): Promise<FileWriteResponse> => {
    const res = await api.post<FileWriteResponse>('/workspace/file', {
      path,
      content,
      overwrite,
    });
    return res.data;
  },

  // Update a file (supporting direct edit or target_content replacement)
  updateFile: async (
    path: string,
    content: string,
    confirm: boolean = true,
    targetContent?: string
  ): Promise<FileUpdateResponse> => {
    const res = await api.put<FileUpdateResponse>('/workspace/file', {
      path,
      content,
      confirm,
      target_content: targetContent || null,
    });
    return res.data;
  },

  // Delete a file or directory
  deleteFile: async (path: string): Promise<{ success: boolean; message: string }> => {
    const res = await api.delete<{ success: boolean; message: string }>('/workspace/file', {
      params: { path },
    });
    return res.data;
  },

  // Generate boilerplate project templates
  createProject: async (projectType: string, name: string): Promise<ProjectCreateResponse> => {
    const res = await api.post<ProjectCreateResponse>('/workspace/project', {
      project_type: projectType,
      name,
    });
    return res.data;
  },
};
