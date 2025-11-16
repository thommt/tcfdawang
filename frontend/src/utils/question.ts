import type { Question, QuestionPayload } from '../types/question';

export interface QuestionFilters {
  keyword?: string;
  type?: 'T2' | 'T3' | 'all';
  tags?: string[];
}

export function questionToPayload(question: Question): QuestionPayload {
  return {
    type: question.type as 'T2' | 'T3',
    source: question.source,
    year: question.year,
    month: question.month,
    suite: question.suite ?? '',
    number: question.number ?? '',
    title: question.title,
    body: question.body,
    tags: [...(question.tags ?? [])],
  };
}

export function filterQuestions(questions: Question[], filters: QuestionFilters): Question[] {
  const keyword = filters.keyword?.trim().toLowerCase() ?? '';
  const typeFilter = filters.type ?? 'all';
  const tags = filters.tags?.filter(Boolean) ?? [];

  return questions.filter((question) => {
    const matchesType = typeFilter === 'all' || question.type === typeFilter;
    const matchesKeyword = keyword
      ? [question.title, question.body, question.source, question.suite ?? '', question.number ?? '']
          .map((field) => field.toLowerCase())
          .some((field) => field.includes(keyword))
      : true;
    const questionTags = question.tags ?? [];
    const matchesTags = tags.length ? tags.every((tag) => questionTags.includes(tag)) : true;
    return matchesType && matchesKeyword && matchesTags;
  });
}

export function paginateQuestions(questions: Question[], page: number, pageSize: number): Question[] {
  const safePage = Math.max(1, page);
  const safeSize = Math.max(1, pageSize);
  const start = (safePage - 1) * safeSize;
  return questions.slice(start, start + safeSize);
}
