<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import BrandMark from './BrandMark.vue'
import { useAuthStore } from '@/stores/auth'
import { useMessageStore } from '@/stores/messages'

const authStore = useAuthStore()
const messageStore = useMessageStore()
const router = useRouter()
const baseNavigation = [
  { label: '首页', to: '/' },
  { label: '赛事中心', to: '/tournaments' },
  { label: '平台公告', to: '/announcements' },
  { label: '消息', to: '/messages', hasDot: true },
]
const navigation = computed(() => authStore.isAdmin
  ? [...baseNavigation, { label: '管理后台', to: '/admin', hasDot: false }]
  : baseNavigation)

onMounted(async () => {
  await authStore.ensureProfile()
  await messageStore.refresh(authStore.token).catch(() => undefined)
})

async function logout() {
  authStore.logout()
  await router.push('/')
}
</script>

<template>
  <header class="site-header">
    <div class="header-inner">
      <RouterLink class="brand" to="/" aria-label="返回首页">
        <BrandMark />
        <span class="brand-copy">
          <strong>栗子杯</strong>
          <small>KURIBOH CUP</small>
        </span>
      </RouterLink>

      <nav class="main-nav" aria-label="主导航">
        <RouterLink
          v-for="item in navigation"
          :key="item.to"
          :class="['nav-link', { 'has-dot': item.hasDot && messageStore.unreadCount > 0 }]"
          :to="item.to"
        >
          {{ item.label }}
          <span v-if="item.to === '/messages' && messageStore.unreadCount" class="unread-badge">{{ Math.min(messageStore.unreadCount, 99) }}</span>
        </RouterLink>
      </nav>

      <div v-if="authStore.user" class="user-nav">
        <RouterLink class="user-profile-link" to="/profile">
          <span class="avatar">{{ authStore.user.nickname.slice(0, 1) }}</span>
          <span>{{ authStore.user.nickname }}</span>
        </RouterLink>
        <button class="logout-button" type="button" @click="logout">退出</button>
      </div>
      <RouterLink v-else class="auth-link" to="/login">登录 / 注册</RouterLink>
    </div>
  </header>
</template>
