export interface DirectionPlanItem {
  title: string;
  summary?: string;
  stance?: string | null;
  structure?: string[];
}

export interface DirectionPlan {
  recommended?: DirectionPlanItem;
  alternatives?: DirectionPlanItem[];
}

export interface QuestionPayload {
  type: 'T2' | 'T3';
  source: string;
  year: number;
  month: number;
  suite?: string | null;
  number?: string | null;
  title: string;
  body: string;
  tags: string[];
  direction_plan?: DirectionPlan | null;
}

export interface Question extends QuestionPayload {
  id: number;
  slug?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FetchTask {
  id: number;
  type: string;
  status: string;
  session_id: number | null;
  answer_id: number | null;
  payload: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FetchQuestionResult {
  slug: string;
  title: string;
  type: string;
  year: number;
  month: number;
  suite?: string;
  number?: string;
  body: string;
  source_url: string;
}
