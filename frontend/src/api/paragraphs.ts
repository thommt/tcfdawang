import apiClient from './http';
import type { Paragraph } from '../types/answer';

export async function fetchParagraphsByAnswer(answerId: number): Promise<Paragraph[]> {
  const response = await apiClient.get<Paragraph[]>(`/answers/${answerId}/paragraphs`);
  return response.data;
}
