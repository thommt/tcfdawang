import { defineStore } from 'pinia';
import type { FetchTask } from '../types/question';
import type { TaskQueryParams } from '../api/tasks';
import { fetchTasks, retryTask, cancelTask } from '../api/tasks';

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
    async retry(taskId: number) {
      const task = await retryTask(taskId);
      await this.load(this.filters);
      return task;
    },
    async cancel(taskId: number) {
      const task = await cancelTask(taskId);
      await this.load(this.filters);
      return task;
    },
  },
});
