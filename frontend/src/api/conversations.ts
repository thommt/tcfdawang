import apiClient from './http';
import type { LLMConversationLog } from '../types/answer';

export interface ConversationQuery {
  limit?: number;
  session_id?: number;
  task_id?: number;
}

export async function fetchConversations(params: ConversationQuery = {}): Promise<LLMConversationLog[]> {
  const response = await apiClient.get<LLMConversationLog[]>('/llm-conversations', {
    params: {
      limit: 50,
      ...params
    }
  });
  return response.data;
}
