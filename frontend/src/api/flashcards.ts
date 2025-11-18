import apiClient from './http';
import type { FlashcardStudyCard, FlashcardProgress } from '../types/flashcard';

export interface FlashcardQuery {
  mode?: 'guided' | 'manual';
  entityType?: 'chunk' | 'sentence' | 'lexeme';
  limit?: number;
  answerId?: number | null;
}

export async function fetchDueFlashcards(options?: FlashcardQuery): Promise<FlashcardStudyCard[]> {
  const { mode = 'manual', entityType, limit = 20, answerId } = options ?? {};
  const params: Record<string, unknown> = {
    mode,
    limit
  };
  if (mode === 'manual' && entityType) {
    params.entity_type = entityType;
  }
  if (typeof answerId === 'number') {
    params.answer_id = answerId;
  }
  const response = await apiClient.get<FlashcardStudyCard[]>('/flashcards', {
    params
  });
  return response.data;
}

export async function reviewFlashcard(cardId: number, score: number): Promise<FlashcardProgress> {
  const response = await apiClient.post<FlashcardProgress>(`/flashcards/${cardId}/review`, null, {
    params: { score }
  });
  return response.data;
}
