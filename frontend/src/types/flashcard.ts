export interface FlashcardProgress {
  id: number;
  entity_type: string;
  entity_id: number;
  last_score?: number | null;
  due_at: string;
  streak: number;
  interval_days: number;
  extra: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SentenceCardInfo {
  id: number;
  paragraph_id: number;
  answer_id?: number | null;
  text: string;
  translation_en?: string | null;
  translation_zh?: string | null;
  difficulty?: string | null;
}

export interface LexemeCardInfo {
  id: number;
  lemma: string;
  sense_label?: string | null;
  gloss?: string | null;
  translation_en?: string | null;
  translation_zh?: string | null;
  sample_sentence?: string | null;
  sample_sentence_translation?: string | null;
}

export interface FlashcardStudyCard {
  card: FlashcardProgress;
  sentence?: SentenceCardInfo | null;
  lexeme?: LexemeCardInfo | null;
}
