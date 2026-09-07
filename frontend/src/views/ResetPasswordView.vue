<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import { prepareViewportForNavigation } from '@/utils/mobileViewport'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const form = reactive({ identifier: '', newPassword: '', confirmPassword: '' })
const submitting = ref(false)
const error = ref('')

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    await authStore.resetPassword(form.identifier, form.newPassword, form.confirmPassword)
    await prepareViewportForNavigation()
    await router.push({
      path: '/login',
      query: {
        reset: 'success',
        ...(typeof route.query.redirect === 'string' ? { redirect: route.query.redirect } : {}),
      },
    })
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '密码重置失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-page page-shell">
    <section class="auth-intro">
      <h1>重置密码</h1>
      <p>输入注册时使用的 QQ 号或手机号，并设置新密码。</p>
    </section>
    <form class="auth-form" @submit.prevent="submit">
      <FormMessage v-if="error" :message="error" />
      <label><span>QQ 号或手机号</span><input v-model.trim="form.identifier" type="tel" inputmode="numeric" autocomplete="username" minlength="5" maxlength="20" required /></label>
      <label><span>新密码</span><input v-model="form.newPassword" type="password" autocomplete="new-password" minlength="6" maxlength="128" required /><small>至少 6 个字符</small></label>
      <label><span>确认新密码</span><input v-model="form.confirmPassword" type="password" autocomplete="new-password" minlength="6" maxlength="128" required /></label>
      <button class="button primary full" type="submit" :disabled="submitting">{{ submitting ? '正在重置…' : '重置密码' }}</button>
      <p class="form-switch">想起密码了？<RouterLink :to="{ path: '/login', query: typeof route.query.redirect === 'string' ? { redirect: route.query.redirect } : {} }">返回登录</RouterLink></p>
    </form>
  </div>
</template>
