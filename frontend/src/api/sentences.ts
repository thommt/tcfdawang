import apiClient from './http';
import type { FetchTask } from '../types/question';

export async function generateSentenceChunks(sentenceId: number): Promise<FetchTask> {
  const response = await apiClient.post<FetchTask>(`/sentences/${sentenceId}/tasks/chunks`, {});
  return response.data;
}

export async function generateChunkLexemes(sentenceId: number): Promise<FetchTask> {
  const response = await apiClient.post<FetchTask>(`/sentences/${sentenceId}/tasks/chunk-lexemes`, {});
  return response.data;
}
