import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/pages/IndexPage.vue'),
        meta: { section: 'dashboard' },
      },
      {
        path: 'document-groups',
        name: 'groups',
        component: () => import('@/pages/IndexPage.vue'),
        meta: { section: 'groups' },
      },
      {
        path: 'documents',
        name: 'documents',
        component: () => import('@/pages/IndexPage.vue'),
        meta: { section: 'documents' },
      },
      {
        path: 'search',
        name: 'search',
        component: () => import('@/pages/IndexPage.vue'),
        meta: { section: 'search' },
      },
      {
        path: 'llm-config',
        name: 'llm',
        component: () => import('@/pages/IndexPage.vue'),
        meta: { section: 'llm' },
      },
      {
        path: 'ai-agent',
        alias: 'api-keys',
        name: 'keys',
        component: () => import('@/pages/IndexPage.vue'),
        meta: { section: 'keys' },
      },
      {
        path: 'agent-playground',
        name: 'playground',
        component: () => import('@/pages/IndexPage.vue'),
        meta: { section: 'playground' },
      },
    ],
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('@/pages/ErrorNotFound.vue'),
  },
];

export default routes;
