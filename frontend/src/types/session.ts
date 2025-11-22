import type { FetchTask } from './question';
import type { LLMConversationLog } from './answer';

export type SessionType = 'first' | 'review';

export interface SessionPayload {
  question_id: number;
  answer_id?: number | null;
  session_type?: SessionType;
  status?: string;
  user_answer_draft?: string | null;
  progress_state?: Record<string, unknown>;
}

export interface Session extends SessionPayload {
  id: number;
  session_type: SessionType;
  status: string;
  started_at: string;
  completed_at: string | null;
}

export interface SessionFinalizePayload {
  group_title?: string;
  answer_group_id?: number;
  group_descriptor?: string;
  dialogue_profile?: Record<string, unknown>;
  answer_title: string;
  answer_text: string;
}

export interface AnswerGroupPayload {
  question_id: number;
  slug?: string | null;
  title: string;
  descriptor?: string | null;
  dialogue_profile?: Record<string, unknown>;
}

export interface AnswerPayload {
  answer_group_id: number;
  version_index?: number;
  status?: string;
  title: string;
  text: string;
}

export interface EvalTaskResult {
  feedback?: string;
  score?: number;
}

export interface SessionHistory {
  session: Session;
  tasks: FetchTask[];
  conversations: LLMConversationLog[];
}

export interface LiveTurn {
  id: number;
  session_id: number;
  turn_index: number;
  candidate_query: string;
  examiner_reply?: string | null;
  candidate_followup?: string | null;
  meta?: Record<string, unknown>;
  created_at: string;
}
