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
  dialogue_profile?: Record<string, unknown>;
  created_at: string;
  answers: Answer[];
}
