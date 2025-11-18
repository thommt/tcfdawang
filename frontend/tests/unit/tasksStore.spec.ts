import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';

import { useTaskStore } from '../../src/stores/tasks';
import * as api from '../../src/api/tasks';

const mockTask = {
  id: 1,
  type: 'eval',
  status: 'succeeded',
  session_id: 2,
  answer_id: null,
  payload: {},
  result_summary: {},
  error_message: null,
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

  it('retries task', async () => {
    vi.spyOn(api, 'fetchTasks').mockResolvedValue([mockTask]);
    const retrySpy = vi.spyOn(api, 'retryTask').mockResolvedValue({
      ...mockTask,
      id: 2,
    });
    const store = useTaskStore();
    await store.retry(1);
    expect(retrySpy).toHaveBeenCalledWith(1);
    retrySpy.mockRestore();
  });

  it('cancels task', async () => {
    vi.spyOn(api, 'fetchTasks').mockResolvedValue([mockTask]);
    const cancelSpy = vi.spyOn(api, 'cancelTask').mockResolvedValue({
      ...mockTask,
      status: 'canceled',
    });
    const store = useTaskStore();
    await store.cancel(1);
    expect(cancelSpy).toHaveBeenCalledWith(1);
    cancelSpy.mockRestore();
  });
});
