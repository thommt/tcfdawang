import { describe, it, expect } from 'vitest';
import { questionToPayload, filterQuestions, paginateQuestions } from '../../src/utils/question';
import type { Question } from '../../src/types/question';

describe('questionToPayload', () => {
  it('converts question to payload', () => {
    const question: Question = {
      id: 10,
      type: 'T3',
      source: 'mock',
      year: 2024,
      month: 9,
      suite: 'B',
      number: '03',
      title: 'Sample',
      body: 'Body',
      tags: ['foo', 'bar'],
      slug: 'RE202409.T3.P02S03',
      created_at: '',
      updated_at: '',
    };
    const payload = questionToPayload(question);
    expect(payload).toEqual({
      type: 'T3',
      source: 'mock',
      year: 2024,
      month: 9,
      suite: 'B',
      number: '03',
      title: 'Sample',
      body: 'Body',
      tags: ['foo', 'bar'],
    });
  });
});

describe('question helpers', () => {
  const baseQuestions: Question[] = [
    {
      id: 1,
      type: 'T2',
      source: 'alpha',
      year: 2024,
      month: 1,
      suite: 'A',
      number: '01',
      title: 'Immigration topic',
      body: 'Discuss immigration policies',
      tags: ['immigration', 'policy'],
      slug: 'RE202401.T2.P01S01',
      created_at: '',
      updated_at: '',
    },
    {
      id: 2,
      type: 'T3',
      source: 'beta',
      year: 2023,
      month: 6,
      suite: 'B',
      number: '02',
      title: 'Family life',
      body: 'Talk about family and work balance',
      tags: ['family'],
      slug: 'OP202306.T3.P02S01',
      created_at: '',
      updated_at: '',
    },
  ];

  it('filters by keyword, type and tags', () => {
    const filtered = filterQuestions(baseQuestions, {
      keyword: 'immigration',
      type: 'T2',
      tags: ['policy'],
    });
    expect(filtered).toHaveLength(1);
    expect(filtered[0].id).toBe(1);
  });

  it('paginates question list', () => {
    const list = [...baseQuestions, { ...baseQuestions[0], id: 3 }];
    const page = paginateQuestions(list, 2, 2);
    expect(page).toHaveLength(1);
    expect(page[0].id).toBe(3);
  });
});
