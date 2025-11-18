import apiClient from './http';
import type { FetchTask } from '../types/question';

export async function splitSentence(sentenceId: number): Promise<FetchTask> {
  const response = await apiClient.post<FetchTask>(`/sentences/${sentenceId}/tasks/split-phrases`, {});
  return response.data;
}
