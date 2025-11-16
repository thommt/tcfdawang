import { setActivePinia, createPinia } from 'pinia';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { useQuestionStore } from '../../src/stores/questions';
import * as api from '../../src/api/questions';

describe('Question Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('loads questions', async () => {
    const mockQuestions = [
      {
        id: 1,
        type: 'T2',
        source: 'mock',
        year: 2024,
        month: 9,
        suite: '1',
        number: '1',
        title: 'Mock question',
        body: 'Body',
        tags: [],
        slug: 'RE202409.T2.P01S01',
        created_at: '',
        updated_at: '',
      },
    ];
    const fetchSpy = vi.spyOn(api, 'fetchQuestions').mockResolvedValue(mockQuestions);
    const store = useQuestionStore();
    await store.load();
    expect(fetchSpy).toHaveBeenCalled();
    expect(store.items).toHaveLength(1);
    fetchSpy.mockRestore();
  });

  it('generates metadata for a question', async () => {
    const store = useQuestionStore();
    store.items = [
      {
        id: 1,
        type: 'T2',
        source: 'mock',
        year: 2024,
        month: 9,
        suite: '1',
        number: '1',
        title: 'Mock question',
        body: 'Body',
        tags: [],
        slug: 'RE202409.T2.P01S01',
        created_at: '',
        updated_at: '',
      },
    ];
    const updated = { ...store.items[0], title: '新标题', tags: ['教育'] };
    const spy = vi.spyOn(api, 'generateQuestionMetadata').mockResolvedValue(updated);
    await store.generateMetadata(1);
    expect(spy).toHaveBeenCalledWith(1);
    expect(store.items[0].title).toBe('新标题');
    expect(store.items[0].tags).toEqual(['教育']);
    spy.mockRestore();
  });
});
