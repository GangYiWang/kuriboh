<script setup lang="ts">
import { ref } from 'vue'

import { apiPost } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import type { MessageSendResponse } from '@/types/message'

const authStore = useAuthStore()
const title = ref('')
const body = ref('')
const busy = ref(false)
const error = ref('')
const message = ref('')

async function send() {
  if (!window.confirm('平台通知会发送给全部已注册账号，确认发送？')) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const result = await apiPost<MessageSendResponse>('/admin/messages/platform', {
      title: title.value,
      body: body.value,
      request_id: crypto.randomUUID(),
    }, authStore.token)
    message.value = `平台通知已发送给 ${result.sent_count} 个账号。`
    title.value = ''
    body.value = ''
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '通知发送失败'
  } finally { busy.value = false }
}
</script>

<template>
  <div class="page-shell admin-page">
    <header class="page-heading"><p class="section-kicker">PLATFORM MESSAGE</p><h1>平台通知</h1><p>向全部已注册账号发送需要关注的重要站内通知。</p></header>
    <FormMessage v-if="message" type="success" :message="message" /><FormMessage v-if="error" :message="error" />
    <form class="content-form notice-form" @submit.prevent="send">
      <label><span>通知标题</span><input v-model.trim="title" minlength="2" maxlength="120" required /></label>
      <label><span>通知正文</span><textarea v-model.trim="body" minlength="2" maxlength="5000" rows="7" required /></label>
      <p class="form-hint">该功能不用于每轮对阵、排名或赛果变化；比赛过程信息仍在赛事模块内查看。</p>
      <button class="button primary" type="submit" :disabled="busy">发送平台通知</button>
    </form>
  </div>
</template>
