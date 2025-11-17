import apiClient from './http';
import type { Session, SessionPayload, SessionFinalizePayload } from '../types/session';
import type { FetchTask } from '../types/question';

const resource = '/sessions';

export async function fetchSessions(): Promise<Session[]> {
  const response = await apiClient.get<Session[]>(resource);
  return response.data;
}

export async function fetchSessionById(id: number): Promise<Session> {
  const response = await apiClient.get<Session>(`${resource}/${id}`);
  return response.data;
}

export async function createSession(payload: SessionPayload): Promise<Session> {
  const response = await apiClient.post<Session>(resource, payload);
  return response.data;
}

export async function updateSession(id: number, payload: Partial<SessionPayload>): Promise<Session> {
  const response = await apiClient.put<Session>(`${resource}/${id}`, payload);
  return response.data;
}

export async function runEvalTask(sessionId: number): Promise<FetchTask> {
  const response = await apiClient.post<FetchTask>(`${resource}/${sessionId}/tasks/eval`, {});
  return response.data;
}

export async function finalizeSession(
  sessionId: number,
  payload: SessionFinalizePayload
): Promise<Session> {
  const response = await apiClient.post<Session>(`${resource}/${sessionId}/finalize`, payload);
  return response.data;
}
