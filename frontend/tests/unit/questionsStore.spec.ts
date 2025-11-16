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
});
