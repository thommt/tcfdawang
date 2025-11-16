import { defineStore } from 'pinia';
import type { Question, QuestionPayload, FetchQuestionResult } from '../types/question';
import { fetchQuestions, createQuestion, updateQuestion, deleteQuestion, runFetchTask, importFetchResultsApi, generateQuestionMetadata } from '../api/questions';

interface State {
  items: Question[];
  loading: boolean;
  error: string | null;
  fetchResults: FetchQuestionResult[];
  fetchSummary: Record<string, number> | null;
  lastFetchTaskId: number | null;
}

export const useQuestionStore = defineStore('questions', {
  state: (): State => ({
    items: [],
    loading: false,
    error: null,
    fetchResults: [],
    fetchSummary: null,
    lastFetchTaskId: null,
  }),
  actions: {
    async load() {
      this.loading = true;
      this.error = null;
      try {
        this.items = await fetchQuestions();
      } catch (err) {
        this.error = '无法加载题目';
        throw err;
      } finally {
        this.loading = false;
      }
    },
    async addQuestion(payload: QuestionPayload) {
      const created = await createQuestion(payload);
      this.items.push(created);
    },
    async updateQuestion(id: number, payload: Partial<QuestionPayload>) {
      const updated = await updateQuestion(id, payload);
      this.items = this.items.map((item) => (item.id === id ? updated : item));
    },
    async removeQuestion(id: number) {
      await deleteQuestion(id);
      this.items = this.items.filter((item) => item.id !== id);
    },
    async runFetch(urls: string[]) {
      const response = await runFetchTask(urls);
      this.fetchResults = response.results;
      this.fetchSummary = {
        count: response.task.result_summary?.count ?? response.results.length,
        t2_count: response.task.result_summary?.t2_count ?? response.results.filter((q) => q.type === 'T2').length,
        t3_count: response.task.result_summary?.t3_count ?? response.results.filter((q) => q.type === 'T3').length,
      };
      this.lastFetchTaskId = response.task.id;
      return response;
    },
    async importFetchResults() {
      if (!this.lastFetchTaskId) {
        throw new Error('暂无可导入的结果');
      }
      const created = await importFetchResultsApi(this.lastFetchTaskId);
      this.items.push(...created);
      this.fetchResults = [];
      this.fetchSummary = null;
      this.lastFetchTaskId = null;
      return created;
    },
    async generateMetadata(questionId: number) {
      const updated = await generateQuestionMetadata(questionId);
      this.items = this.items.map((item) => (item.id === questionId ? updated : item));
      return updated;
    },
  },
});
