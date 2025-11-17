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
  },
  {
    path: '/questions/:id',
    name: 'question-detail',
    component: () => import('../views/QuestionDetailView')
  },
  {
    path: '/sessions/:id',
    name: 'session-workspace',
    component: () => import('../views/SessionWorkspaceView')
  },
  {
    path: '/answers/:id',
    name: 'answer-detail',
    component: () => import('../views/AnswerDetailView')
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
