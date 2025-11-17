import apiClient from './http';
import type { Answer } from '../types/answer';

const resource = '/answers';

export async function fetchAnswerById(id: number): Promise<Answer> {
  const response = await apiClient.get<Answer>(`${resource}/${id}`);
  return response.data;
}
