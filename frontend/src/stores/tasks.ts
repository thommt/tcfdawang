import { defineStore } from 'pinia';
import type { FetchTask } from '../types/question';
import type { TaskQueryParams } from '../api/tasks';
import { fetchTasks } from '../api/tasks';

interface State {
  items: FetchTask[];
  loading: boolean;
  error: string | null;
  filters: TaskQueryParams;
}

export const useTaskStore = defineStore('tasks', {
  state: (): State => ({
    items: [],
    loading: false,
    error: null,
    filters: {},
  }),
  actions: {
    async load(params: TaskQueryParams = {}) {
      this.loading = true;
      this.error = null;
      this.filters = params;
      try {
        this.items = await fetchTasks(params);
      } catch (error) {
        this.error = '无法加载任务列表';
        throw error;
      } finally {
        this.loading = false;
      }
    },
  },
});
