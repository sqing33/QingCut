import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/capture',
    },
    {
      path: '/capture',
      name: 'capture',
      component: () => import('@/views/VideoCapturePage.vue'),
    },
    {
      path: '/data',
      name: 'data',
      component: () => import('@/views/DataPage.vue'),
    },
    {
      path: '/train',
      name: 'train',
      component: () => import('@/views/Train.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/Settings.vue'),
    },
  ],
})

export default router
