import { defineStore } from 'pinia';
import type { Session, SessionPayload, SessionFinalizePayload, SessionHistory } from '../types/session';
import type { FetchTask } from '../types/question';
import {
  fetchSessions,
  fetchSessionById,
  createSession as createSessionApi,
  updateSession as updateSessionApi,
  runEvalTask,
  runComposeTask,
  finalizeSession as finalizeSessionApi,
  fetchSessionHistory,
  createReviewSession as createReviewSessionApi,
} from '../api/sessions';

interface State {
  sessions: Session[];
  currentSession: Session | null;
  history: SessionHistory | null;
  historyLoading: boolean;
  loading: boolean;
  error: string | null;
  lastTask: FetchTask | null;
}

export const useSessionStore = defineStore('sessions', {
  state: (): State => ({
    sessions: [],
    currentSession: null,
    history: null,
    historyLoading: false,
    loading: false,
    error: null,
    lastTask: null,
  }),
  actions: {
    async loadSessions() {
      this.loading = true;
      this.error = null;
      try {
        this.sessions = await fetchSessions();
      } catch (error) {
        this.error = '无法加载学习记录';
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async loadSession(sessionId: number) {
      this.loading = true;
      this.error = null;
      try {
        const session = await fetchSessionById(sessionId);
        this.currentSession = session;
        const known = this.sessions.find((item) => item.id === session.id);
        if (known) {
          Object.assign(known, session);
        } else {
          this.sessions.push(session);
        }
      } catch (error) {
        this.error = '无法获取 Session';
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async createSession(questionId: number) {
      const payload: SessionPayload = { question_id: questionId };
      const session = await createSessionApi(payload);
      this.sessions.push(session);
      this.currentSession = session;
      return session;
    },
    async createReviewSession(answerId: number) {
      const session = await createReviewSessionApi(answerId);
      this.sessions.push(session);
      this.currentSession = session;
      return session;
    },
    async updateSession(sessionId: number, payload: Partial<SessionPayload>) {
      const updated = await updateSessionApi(sessionId, payload);
      this.currentSession = updated;
      this.sessions = this.sessions.map((session) => (session.id === sessionId ? updated : session));
      return updated;
    },
    async saveDraft(sessionId: number, draft: string) {
      return this.updateSession(sessionId, { user_answer_draft: draft });
    },
    async loadSessionHistory(sessionId: number) {
      this.historyLoading = true;
      try {
        this.history = await fetchSessionHistory(sessionId);
      } finally {
        this.historyLoading = false;
      }
    },
    async triggerEval(sessionId: number) {
      const task = await runEvalTask(sessionId);
      this.lastTask = task;
      await this.loadSession(sessionId);
      await this.loadSessionHistory(sessionId);
      return task;
    },
    async composeAnswer(sessionId: number) {
      const task = await runComposeTask(sessionId);
      this.lastTask = task;
      await this.loadSession(sessionId);
      await this.loadSessionHistory(sessionId);
      return task;
    },
    async finalizeSession(sessionId: number, payload: SessionFinalizePayload) {
      const session = await finalizeSessionApi(sessionId, payload);
      this.currentSession = session;
      this.sessions = this.sessions.map((item) => (item.id === sessionId ? session : item));
      await this.loadSessionHistory(sessionId);
      return session;
    },
    sessionsByQuestion(questionId: number) {
      return this.sessions.filter((session) => session.question_id === questionId);
    },
  },
});
