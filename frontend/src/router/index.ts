import { createRouter, createWebHistory } from 'vue-router'

import { routes } from './routes'
import {
  MESSAGING_ENABLED,
  TOURNAMENT_AUDIT_VIEW_ENABLED,
  TOURNAMENT_NOTIFICATIONS_ENABLED,
} from '@/config/features'
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
  if (!MESSAGING_ENABLED && (to.name === 'messages' || to.name === 'admin-messages')) return '/'
  const tournamentSection = typeof to.params.section === 'string' ? to.params.section : ''
  if (
    (!TOURNAMENT_NOTIFICATIONS_ENABLED && tournamentSection === 'notifications')
    || (!TOURNAMENT_AUDIT_VIEW_ENABLED && tournamentSection === 'audit')
  ) {
    return `/tournaments/${String(to.params.id)}/manage/settings`
  }

  const authStore = useAuthStore()
  await authStore.ensureProfile()
  if (to.meta.guestOnly && authStore.isAuthenticated) return '/profile'
  if ((to.meta.requiresAuth || to.meta.requiresPlatformAdmin) && !authStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresPlatformAdmin && !authStore.isPlatformAdmin) return '/'
})

export default router
