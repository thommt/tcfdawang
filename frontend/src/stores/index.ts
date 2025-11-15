import { defineStore } from 'pinia';

export const useAppStore = defineStore('app', {
  state: () => ({
    message: '准备实现 spec 中的功能'
  })
});
