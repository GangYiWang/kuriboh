<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { apiGet } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import type { QqOAuthStatus } from '@/types/auth'

const authStore = useAuthStore()
const form = reactive({ current: '', next: '', confirm: '' })
const message = ref('')
const error = ref('')
const qqStatus = ref<QqOAuthStatus | null>(null)
const passwordFormOpen = ref(false)

onMounted(async () => {
  qqStatus.value = await apiGet<QqOAuthStatus>('/auth/qq/status').catch(() => null)
  const pendingBinding = sessionStorage.getItem('lizibei_qq_binding_token')
  if (pendingBinding) {
    try {
      await authStore.bindQq(pendingBinding)
      sessionStorage.removeItem('lizibei_qq_binding_token')
      message.value = 'QQ 授权已绑定。'
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'QQ 绑定失败'
    }
  }
})

async function changePassword() {
  message.value = ''
  error.value = ''
  try {
    await authStore.changePassword(form.current, form.next, form.confirm)
    form.current = ''
    form.next = ''
    form.confirm = ''
    message.value = '密码已更新。'
    passwordFormOpen.value = false
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '密码修改失败'
  }
}

function openPasswordForm() {
  message.value = ''
  error.value = ''
  passwordFormOpen.value = true
}

function closePasswordForm() {
  form.current = ''
  form.next = ''
  form.confirm = ''
  error.value = ''
  passwordFormOpen.value = false
}
</script>

<template>
  <div class="page-shell account-page">
    <header class="page-heading">
      <p class="section-kicker">ACCOUNT</p>
      <h1>个人中心</h1>
      <p>账号基础资料与登录安全。</p>
    </header>
    <FormMessage v-if="message" type="success" :message="message" />
    <FormMessage v-if="error && !passwordFormOpen" :message="error" />
    <div v-if="authStore.user" :class="['account-layout', { 'password-form-open': passwordFormOpen }]">
      <section class="profile-details">
        <h2>账号资料</h2>
        <dl class="definition-list">
          <div><dt>昵称</dt><dd>{{ authStore.user.nickname }}</dd></div>
          <div v-if="authStore.user.phone_number"><dt>手机号</dt><dd>{{ authStore.user.phone_number }}</dd></div>
          <div v-if="authStore.user.qq_number"><dt>QQ 号</dt><dd>{{ authStore.user.qq_number }}</dd></div>
          <div><dt>角色</dt><dd>{{ authStore.isAdmin ? '赛事管理员' : '参赛选手' }}</dd></div>
          <div><dt>QQ 授权</dt><dd>{{ authStore.user.qq_bound ? '已绑定' : '未绑定' }}</dd></div>
        </dl>
        <p class="form-hint">登录账号和昵称当前不可修改。</p>
        <a v-if="!authStore.user.qq_bound && qqStatus?.configured" class="button secondary qq-bind-button" :href="qqStatus.authorization_url ?? '#'">绑定 QQ 授权</a>
        <section class="security-settings" aria-labelledby="security-settings-title">
          <div>
            <h2 id="security-settings-title">账号安全</h2>
            <p>定期更新登录密码可以提高账号安全性。</p>
          </div>
          <button
            class="button secondary"
            type="button"
            aria-controls="password-settings-form"
            :aria-expanded="passwordFormOpen"
            @click="openPasswordForm"
          >修改密码</button>
        </section>
      </section>
      <form
        v-if="passwordFormOpen"
        id="password-settings-form"
        class="settings-form"
        @submit.prevent="changePassword"
      >
        <h2>修改密码</h2>
        <FormMessage v-if="error" :message="error" />
        <label><span>当前密码</span><input v-model="form.current" type="password" autocomplete="current-password" required /></label>
        <label><span>新密码</span><input v-model="form.next" type="password" minlength="6" autocomplete="new-password" required /></label>
        <label><span>确认新密码</span><input v-model="form.confirm" type="password" minlength="6" autocomplete="new-password" required /></label>
        <div class="form-actions password-form-actions">
          <button class="button primary" type="submit">保存新密码</button>
          <button class="button secondary" type="button" @click="closePasswordForm">取消</button>
        </div>
      </form>
    </div>
  </div>
</template>
