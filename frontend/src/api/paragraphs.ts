import apiClient from './http';
import type { Paragraph } from '../types/answer';
import type { FetchTask } from '../types/question';

export async function fetchParagraphsByAnswer(answerId: number): Promise<Paragraph[]> {
  const response = await apiClient.get<Paragraph[]>(`/answers/${answerId}/paragraphs`);
  return response.data;
}

export async function runStructureTask(answerId: number): Promise<FetchTask> {
  const response = await apiClient.post<FetchTask>(`/answers/${answerId}/tasks/structure`, {});
  return response.data;
}
