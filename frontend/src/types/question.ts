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
}

export interface Question extends QuestionPayload {
  id: number;
  created_at: string;
  updated_at: string;
}

export interface FetchTask {
  id: number;
  type: string;
  status: string;
  result_summary: Record<string, unknown>;
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
