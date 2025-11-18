import apiClient from './http';
import type { Answer, AnswerHistory } from '../types/answer';

const resource = '/answers';

export async function fetchAnswerById(id: number): Promise<Answer> {
  const response = await apiClient.get<Answer>(`${resource}/${id}`);
  return response.data;
}

export async function fetchAnswerHistory(id: number): Promise<AnswerHistory> {
  const response = await apiClient.get<AnswerHistory>(`${resource}/${id}/history`);
  return response.data;
}

export async function deleteAnswer(id: number): Promise<void> {
  await apiClient.delete(`${resource}/${id}`);
}
