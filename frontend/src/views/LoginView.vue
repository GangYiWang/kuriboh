<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { apiGet } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import type { QqOAuthStatus } from '@/types/auth'
import { prepareViewportForNavigation } from '@/utils/mobileViewport'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const identifier = ref('')
const password = ref('')
const submitting = ref(false)
const message = ref(route.query.qq === 'bind' ? 'QQ 授权成功，请先登录现有账号完成绑定。' : '')
const error = ref('')
const qqStatus = ref<QqOAuthStatus | null>(null)

onMounted(async () => {
  qqStatus.value = await apiGet<QqOAuthStatus>('/auth/qq/status').catch(() => null)
})

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    await authStore.login(identifier.value, password.value)
    const pendingBinding = sessionStorage.getItem('lizibei_qq_binding_token')
    if (pendingBinding) {
      await authStore.bindQq(pendingBinding)
      sessionStorage.removeItem('lizibei_qq_binding_token')
    }
    await prepareViewportForNavigation()
    await router.push(typeof route.query.redirect === 'string' ? route.query.redirect : '/')
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '登录失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-page page-shell">
    <section class="auth-intro">
      <h1>登录栗子杯</h1>
      <p>使用注册时填写的 QQ 号或手机号登录。</p>
    </section>
    <form class="auth-form" @submit.prevent="submit">
      <FormMessage v-if="message" type="success" :message="message" />
      <FormMessage v-if="error" :message="error" />
      <label><span>QQ 号或手机号</span><input v-model.trim="identifier" type="tel" inputmode="numeric" autocomplete="username" minlength="5" maxlength="20" required /></label>
      <label><span>密码</span><input v-model="password" type="password" autocomplete="current-password" required /></label>
      <button class="button primary full" type="submit" :disabled="submitting">{{ submitting ? '正在登录…' : '登录' }}</button>
      <a v-if="qqStatus?.configured" class="button secondary full" :href="qqStatus.authorization_url ?? '#'">使用 QQ 授权登录</a>
      <p class="form-switch">还没有账号？<RouterLink :to="{ path: '/register', query: typeof route.query.redirect === 'string' ? { redirect: route.query.redirect } : {} }">立即注册</RouterLink></p>
    </form>
  </div>
</template>
