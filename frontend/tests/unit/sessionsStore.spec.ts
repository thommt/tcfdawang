import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';

import { useSessionStore } from '../../src/stores/sessions';
import * as api from '../../src/api/sessions';

const mockSession = {
  id: 1,
  question_id: 10,
  session_type: 'first' as const,
  status: 'draft',
  started_at: new Date().toISOString(),
  completed_at: null,
  answer_id: null,
  user_answer_draft: '',
  progress_state: {},
};

describe('Session Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('loads sessions', async () => {
    const loadSpy = vi.spyOn(api, 'fetchSessions').mockResolvedValue([mockSession]);
    const store = useSessionStore();
    await store.loadSessions();
    expect(store.sessions).toHaveLength(1);
    expect(loadSpy).toHaveBeenCalled();
    loadSpy.mockRestore();
  });

  it('runs eval task and refreshes session', async () => {
    vi.spyOn(api, 'fetchSessions').mockResolvedValue([mockSession]);
    const sessionSpy = vi.spyOn(api, 'fetchSessionById').mockResolvedValue({
      ...mockSession,
      progress_state: { last_eval: { feedback: 'Great', score: 5 } },
    });
    const evalSpy = vi.spyOn(api, 'runEvalTask').mockResolvedValue({
      id: 99,
      type: 'eval',
      status: 'succeeded',
      payload: { session_id: 1 },
      result_summary: { score: 5 },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    const store = useSessionStore();
    store.sessions = [mockSession];
    store.currentSession = mockSession;
    await store.triggerEval(1);
    expect(evalSpy).toHaveBeenCalledWith(1);
    expect(sessionSpy).toHaveBeenCalled();
    expect(store.lastTask?.type).toBe('eval');
    evalSpy.mockRestore();
    sessionSpy.mockRestore();
  });

  it('finalizes session', async () => {
    const finalizeSpy = vi.spyOn(api, 'finalizeSession').mockResolvedValue({
      ...mockSession,
      status: 'completed',
      answer_id: 2,
      completed_at: new Date().toISOString(),
    });
    const store = useSessionStore();
    store.sessions = [mockSession];
    store.currentSession = mockSession;
    const payload = { answer_title: 'Final', answer_text: 'Body' };
    await store.finalizeSession(1, payload);
    expect(finalizeSpy).toHaveBeenCalledWith(1, payload);
    expect(store.currentSession?.status).toBe('completed');
    finalizeSpy.mockRestore();
  });
});
