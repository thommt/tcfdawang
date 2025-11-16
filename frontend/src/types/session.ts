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
