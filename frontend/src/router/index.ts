import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/questions'
  },
  {
    path: '/questions',
    name: 'questions',
    component: () => import('../views/QuestionsView')
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
