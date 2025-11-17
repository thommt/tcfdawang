import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';

import { useTaskStore } from '../../src/stores/tasks';
import * as api from '../../src/api/tasks';

const mockTask = {
  id: 1,
  type: 'eval',
  status: 'succeeded',
  session_id: 2,
  payload: {},
  result_summary: {},
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('Task Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('loads tasks', async () => {
    const spy = vi.spyOn(api, 'fetchTasks').mockResolvedValue([mockTask]);
    const store = useTaskStore();
    await store.load();
    expect(store.items).toHaveLength(1);
    expect(spy).toHaveBeenCalled();
    spy.mockRestore();
  });
});
