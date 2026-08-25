<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({
  identifier_type: 'QQ' as 'PHONE' | 'QQ',
  identifier: '',
  nickname: '',
  password: '',
  confirm_password: '',
})
const error = ref('')
const submitting = ref(false)

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    await authStore.register(form)
    await router.push(typeof route.query.redirect === 'string' ? route.query.redirect : '/')
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
      <p>网站昵称应与 Master Duel 游戏内昵称保持一致。</p>
    </section>
    <form class="auth-form" @submit.prevent="submit">
      <FormMessage v-if="error" :message="error" />
      <label>
        <span>注册方式</span>
        <select v-model="form.identifier_type">
          <option value="QQ">QQ 号</option>
          <option value="PHONE">手机号</option>
        </select>
      </label>
      <label>
        <span>{{ form.identifier_type === 'PHONE' ? '手机号' : 'QQ 号' }}</span>
        <input
          v-model.trim="form.identifier"
          type="tel"
          inputmode="numeric"
          autocomplete="username"
          :minlength="form.identifier_type === 'PHONE' ? 11 : 5"
          :maxlength="form.identifier_type === 'PHONE' ? 11 : 20"
          required
        />
        <small>{{ form.identifier_type === 'PHONE' ? '请输入 11 位中国大陆手机号' : '请输入 5～20 位 QQ 号' }}</small>
      </label>
      <label><span>昵称</span><input v-model.trim="form.nickname" autocomplete="nickname" minlength="2" maxlength="30" required /></label>
      <label><span>密码</span><input v-model="form.password" type="password" autocomplete="new-password" minlength="6" required /><small>至少 6 个字符</small></label>
      <label><span>确认密码</span><input v-model="form.confirm_password" type="password" autocomplete="new-password" minlength="6" required /></label>
      <button class="button primary full" type="submit" :disabled="submitting">{{ submitting ? '正在创建…' : '注册并登录' }}</button>
      <p class="form-switch">已有账号？<RouterLink :to="{ path: '/login', query: typeof route.query.redirect === 'string' ? { redirect: route.query.redirect } : {} }">返回登录</RouterLink></p>
    </form>
  </div>
</template>
