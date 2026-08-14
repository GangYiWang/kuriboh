import { createRouter, createWebHistory } from 'vue-router'

import { routes } from './routes'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? `${to.meta.title} · 栗子杯` : '栗子杯'
  document.title = title
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  await authStore.ensureProfile()
  if (to.meta.guestOnly && authStore.isAuthenticated) return '/profile'
  if ((to.meta.requiresAuth || to.meta.requiresAdmin) && !authStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !authStore.isAdmin) return '/'
})

export default router
