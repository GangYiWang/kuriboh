<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const form = reactive({ qq_number: '', nickname: '', password: '', confirm_password: '' })
const error = ref('')
const submitting = ref(false)

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    await authStore.register(form)
    await router.push('/profile')
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '注册失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-page page-shell">
    <section class="auth-intro">
      <p class="section-kicker">CREATE ACCOUNT</p>
      <h1>创建参赛账号</h1>
      <p>QQ 号和昵称注册后不可修改；网站昵称应与 Master Duel 游戏内昵称保持一致。</p>
    </section>
    <form class="auth-form" @submit.prevent="submit">
      <FormMessage v-if="error" :message="error" />
      <label><span>QQ 号</span><input v-model.trim="form.qq_number" inputmode="numeric" autocomplete="username" minlength="5" maxlength="20" required /></label>
      <label><span>昵称</span><input v-model.trim="form.nickname" autocomplete="nickname" minlength="2" maxlength="30" required /></label>
      <label><span>密码</span><input v-model="form.password" type="password" autocomplete="new-password" minlength="8" required /><small>至少 8 个字符</small></label>
      <label><span>确认密码</span><input v-model="form.confirm_password" type="password" autocomplete="new-password" minlength="8" required /></label>
      <button class="button primary full" type="submit" :disabled="submitting">{{ submitting ? '正在创建…' : '注册并登录' }}</button>
      <p class="form-switch">已有账号？<RouterLink to="/login">返回登录</RouterLink></p>
    </form>
  </div>
</template>
