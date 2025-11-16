import { defineStore } from 'pinia';
import type { Question, QuestionPayload, FetchQuestionResult } from '../types/question';
import { fetchQuestions, createQuestion, updateQuestion, deleteQuestion, runFetchTask } from '../api/questions';

interface State {
  items: Question[];
  loading: boolean;
  error: string | null;
  fetchResults: FetchQuestionResult[];
}

export const useQuestionStore = defineStore('questions', {
  state: (): State => ({
    items: [],
    loading: false,
    error: null,
    fetchResults: [],
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
      return response;
    },
  },
});
