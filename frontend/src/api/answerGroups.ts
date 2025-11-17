import apiClient from './http';
import type { AnswerGroup } from '../types/answer';

export async function fetchAnswerGroups(questionId: number): Promise<AnswerGroup[]> {
  const response = await apiClient.get<AnswerGroup[]>(`/answer-groups/by-question/${questionId}`);
  return response.data;
}

export async function fetchAnswerGroupById(groupId: number): Promise<AnswerGroup> {
  const response = await apiClient.get<AnswerGroup>(`/answer-groups/${groupId}`);
  return response.data;
}
