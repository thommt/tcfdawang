import apiClient from './http';
import type { FetchTask } from '../types/question';

export interface TaskQueryParams {
  session_id?: number;
  question_id?: number;
  task_type?: string;
  status?: string;
  answer_id?: number;
}

export async function fetchTasks(params: TaskQueryParams = {}): Promise<FetchTask[]> {
  const response = await apiClient.get<FetchTask[]>('/tasks', { params });
  return response.data;
}

export async function fetchTaskById(id: number): Promise<FetchTask> {
  const response = await apiClient.get<FetchTask>(`/tasks/${id}`);
  return response.data;
}

export async function retryTask(id: number): Promise<FetchTask> {
  const response = await apiClient.post<FetchTask>(`/tasks/${id}/retry`, {});
  return response.data;
}

export async function cancelTask(id: number): Promise<FetchTask> {
  const response = await apiClient.post<FetchTask>(`/tasks/${id}/cancel`, {});
  return response.data;
}
