<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiGet } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import { useMessageStore } from '@/stores/messages'
import type { MessageItem, MessageListResponse } from '@/types/message'
import { messageTypeText } from '@/types/message'

const authStore = useAuthStore()
const messageStore = useMessageStore()
const router = useRouter()
const data = ref<MessageListResponse | null>(null)
const error = ref('')
const busy = ref(false)
const formatTime = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

async function load() {
  data.value = await apiGet<MessageListResponse>('/messages', undefined, authStore.token)
  messageStore.unreadCount = data.value.unread_count
}

async function openMessage(item: MessageItem) {
  if (!item.read_at) {
    await messageStore.markRead(item.id, authStore.token)
    item.read_at = new Date().toISOString()
  }
  if (item.action_url) await router.push(item.action_url)
}

async function markAllRead() {
  busy.value = true
  try {
    await messageStore.markAllRead(authStore.token)
    data.value?.items.forEach((item) => { if (!item.read_at) item.read_at = new Date().toISOString() })
    if (data.value) data.value.unread_count = 0
  } finally { busy.value = false }
}

onMounted(() => load().catch((caught) => { error.value = caught instanceof Error ? caught.message : '消息加载失败' }))
</script>

<template>
  <div class="page-shell content-list-page message-center-page">
    <header class="page-heading split-heading">
      <div><p class="section-kicker">IMPORTANT NOTICE</p><h1>消息中心</h1><p>只收录需要关注的报名结果、人工通知和周报发布。</p></div>
      <button v-if="data?.unread_count" class="button secondary small" type="button" :disabled="busy" @click="markAllRead">全部标为已读</button>
    </header>
    <FormMessage v-if="error" :message="error" />
    <div v-if="data?.items.length" class="message-list">
      <article v-for="item in data.items" :key="item.id" :class="['message-row', { unread: !item.read_at }]">
        <button type="button" @click="openMessage(item)">
          <span class="message-state">{{ item.read_at ? '已读' : '未读' }}</span>
          <div><small>{{ messageTypeText[item.type] }} · {{ formatTime(item.created_at) }}</small><strong>{{ item.title }}</strong><p>{{ item.body }}</p></div>
          <i>{{ item.action_url ? '→' : '' }}</i>
        </button>
      </article>
    </div>
    <div v-else-if="data" class="empty-content"><h2>暂无消息</h2><p>重要通知到达后会显示在这里。</p></div>
  </div>
</template>
