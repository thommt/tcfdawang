import apiClient from './http';
import type { FlashcardStudyCard, FlashcardProgress } from '../types/flashcard';

export async function fetchDueFlashcards(
  entityType?: 'sentence' | 'chunk' | 'lexeme',
  limit = 20
): Promise<FlashcardStudyCard[]> {
  const response = await apiClient.get<FlashcardStudyCard[]>('/flashcards', {
    params: {
      entity_type: entityType,
      limit
    }
  });
  return response.data;
}

export async function reviewFlashcard(cardId: number, score: number): Promise<FlashcardProgress> {
  const response = await apiClient.post<FlashcardProgress>(`/flashcards/${cardId}/review`, null, {
    params: { score }
  });
  return response.data;
}
