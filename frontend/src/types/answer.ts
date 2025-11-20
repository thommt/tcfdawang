import type { Session } from './session';
import type { FetchTask } from './question';

export interface Answer {
  id: number;
  answer_group_id: number;
  version_index: number;
  status: string;
  title: string;
  text: string;
  created_at: string;
}

export interface AnswerGroup {
  id: number;
  question_id: number;
  slug?: string | null;
  title: string;
  descriptor?: string | null;
  direction_descriptor?: string | null;
  dialogue_profile?: Record<string, unknown>;
  created_at: string;
  answers: Answer[];
}

export interface Sentence {
  id: number;
  paragraph_id: number;
  order_index: number;
  text: string;
  translation_en?: string | null;
  translation_zh?: string | null;
  difficulty?: string | null;
  extra: Record<string, unknown>;
  created_at: string;
  chunks: SentenceChunk[];
}

export interface Lexeme {
  id: number;
  headword: string;
  sense_label?: string | null;
  gloss?: string | null;
  translation_en?: string | null;
  translation_zh?: string | null;
  pos_tags?: string | null;
  difficulty?: string | null;
  hash: string;
  extra: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ChunkLexemeUsage {
  id: number;
  chunk_id: number;
  lexeme_id: number;
  order_index: number;
  role?: string | null;
  lexeme: Lexeme;
}

export interface SentenceChunk {
  id: number;
  sentence_id: number;
  order_index: number;
  text: string;
  translation_en?: string | null;
  translation_zh?: string | null;
  chunk_type?: string | null;
  extra?: Record<string, unknown>;
  lexemes: ChunkLexemeUsage[];
}

export interface Paragraph {
  id: number;
  answer_id: number;
  order_index: number;
  role_label?: string | null;
  summary?: string | null;
  extra: Record<string, unknown>;
  created_at: string;
  sentences: Sentence[];
}

export interface LLMConversationLog {
  id: number;
  session_id: number | null;
  task_id: number | null;
  purpose: string;
  messages: Record<string, unknown>;
  result: Record<string, unknown>;
  model_name?: string | null;
  latency_ms?: number | null;
  created_at: string;
}

export interface AnswerHistory {
  answer: Answer;
  group: AnswerGroup;
  sessions: Session[];
  tasks: FetchTask[];
  conversations: LLMConversationLog[];
}
