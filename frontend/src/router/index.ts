import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/questions'
  },
  {
    path: '/questions',
    name: 'questions',
    component: () => import('../views/QuestionsView.tsx')
  },
  {
    path: '/questions/:id',
    name: 'question-detail',
    component: () => import('../views/QuestionDetailView.tsx')
  },
  {
    path: '/sessions/:id',
    name: 'session-workspace',
    component: () => import('../views/SessionWorkspaceView.tsx')
  },
  {
    path: '/answers/:id',
    name: 'answer-detail',
    component: () => import('../views/AnswerDetailView.tsx')
  },
  {
    path: '/tasks',
    name: 'tasks',
    component: () => import('../views/TaskListView.tsx')
  },
  {
    path: '/flashcards',
    name: 'flashcards',
    component: () => import('../views/FlashcardsView.tsx')
  },
  {
    path: '/llm-conversations',
    name: 'llm-conversations',
    component: () => import('../views/ConversationsView.tsx')
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
