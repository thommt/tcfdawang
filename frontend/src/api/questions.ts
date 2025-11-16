import apiClient from './http';
import type { Question, QuestionPayload, FetchQuestionResult, FetchTask } from '../types/question';

const resource = '/questions';

export async function fetchQuestions(): Promise<Question[]> {
  const response = await apiClient.get<Question[]>(resource);
  return response.data;
}

export async function createQuestion(payload: QuestionPayload): Promise<Question> {
  const response = await apiClient.post<Question>(resource, payload);
  return response.data;
}

export async function updateQuestion(id: number, payload: Partial<QuestionPayload>): Promise<Question> {
  const response = await apiClient.put<Question>(`${resource}/${id}`, payload);
  return response.data;
}

export async function deleteQuestion(id: number): Promise<void> {
  await apiClient.delete(`${resource}/${id}`);
}

export async function fetchQuestionById(id: number): Promise<Question> {
  const response = await apiClient.get<Question>(`${resource}/${id}`);
  return response.data;
}

export interface FetchResponse {
  task: FetchTask;
  results: FetchQuestionResult[];
}

export async function runFetchTask(urls: string[]): Promise<FetchResponse> {
  const response = await apiClient.post<FetchResponse>(`${resource}/fetch`, { urls });
  return response.data;
}

export async function getFetchResults(taskId: number): Promise<FetchQuestionResult[]> {
  const response = await apiClient.get<FetchQuestionResult[]>(`${resource}/fetch/results`, {
    params: { task_id: taskId },
  });
  return response.data;
}

export async function importFetchResultsApi(taskId: number): Promise<Question[]> {
  const response = await apiClient.post<Question[]>(`${resource}/fetch/import`, { task_id: taskId });
  return response.data;
}

export async function generateQuestionMetadata(id: number): Promise<Question> {
  const response = await apiClient.post<Question>(`${resource}/${id}/generate-metadata`, {});
  return response.data;
}
