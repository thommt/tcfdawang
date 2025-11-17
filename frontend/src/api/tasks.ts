import apiClient from './http';
import type { FetchTask } from '../types/question';

export interface TaskQueryParams {
  session_id?: number;
  question_id?: number;
  task_type?: string;
  status?: string;
}

export async function fetchTasks(params: TaskQueryParams = {}): Promise<FetchTask[]> {
  const response = await apiClient.get<FetchTask[]>('/tasks', { params });
  return response.data;
}

export async function fetchTaskById(id: number): Promise<FetchTask> {
  const response = await apiClient.get<FetchTask>(`/tasks/${id}`);
  return response.data;
}
