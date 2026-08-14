<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { apiGet } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { TokenResponse, User } from '@/types/auth'

interface CallbackResponse {
  requires_binding: boolean
  access_token: string | null
  binding_token: string | null
  token_type: 'bearer'
  user: User | null
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const status = ref('正在验证 QQ 授权…')

onMounted(async () => {
  const code = typeof route.query.code === 'string' ? route.query.code : ''
  const state = typeof route.query.state === 'string' ? route.query.state : ''
  if (!code || !state) {
    status.value = 'QQ 授权参数不完整'
    return
  }
  try {
    const result = await apiGet<CallbackResponse>(`/auth/qq/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`)
    if (result.requires_binding && result.binding_token) {
      sessionStorage.setItem('lizibei_qq_binding_token', result.binding_token)
      await router.replace({ path: '/login', query: { qq: 'bind' } })
      return
    }
    if (result.access_token && result.user) {
      authStore.acceptSession(result as TokenResponse)
      await router.replace('/profile')
      return
    }
    status.value = 'QQ 授权结果无法识别'
  } catch (error) {
    status.value = error instanceof Error ? error.message : 'QQ 授权失败'
  }
})
</script>

<template><div class="page-shell placeholder-page"><p>{{ status }}</p></div></template>
