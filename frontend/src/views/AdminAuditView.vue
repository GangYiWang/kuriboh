<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { apiGet } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import type { AuditLogListResponse } from '@/types/message'
import { auditActionText } from '@/types/message'

const authStore = useAuthStore()
const data = ref<AuditLogListResponse | null>(null)
const error = ref('')
const loadingMore = ref(false)
const loadMoreError = ref('')
const formatTime = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value))

async function loadAuditLogs(append = false) {
  const offset = append ? data.value?.items.length ?? 0 : 0
  const response = await apiGet<AuditLogListResponse>(`/admin/audit-logs?offset=${offset}&limit=20`, undefined, authStore.token)
  data.value = append && data.value
    ? { items: [...data.value.items, ...response.items], total: response.total }
    : response
}

async function loadMore() {
  loadingMore.value = true
  loadMoreError.value = ''
  try {
    await loadAuditLogs(true)
  } catch (caught) {
    loadMoreError.value = caught instanceof Error ? caught.message : '更多审计记录加载失败'
  } finally {
    loadingMore.value = false
  }
}

onMounted(() => loadAuditLogs()
  .catch((caught) => { error.value = caught instanceof Error ? caught.message : '审计日志加载失败' }))
</script>

<template>
  <div class="page-shell admin-page">
    <header class="page-heading"><h1>操作审计</h1><p>查看影响赛事公平性、审核结果和不可逆发布的关键操作。</p></header>
    <FormMessage v-if="error" :message="error" />
    <div v-if="data?.items.length" class="audit-list">
      <article v-for="item in data.items" :key="item.id" class="audit-row"><time>{{ formatTime(item.created_at) }}</time><div><strong>{{ auditActionText(item.action_type) }}</strong><p>{{ item.operator_nickname }} · {{ item.target_type }} / {{ item.target_id }}</p></div><details><summary>数据变化</summary><pre>{{ JSON.stringify({ before: item.before_json, after: item.after_json }, null, 2) }}</pre></details></article>
      <div v-if="data.items.length < data.total" class="form-actions tournament-load-more"><button class="button secondary" type="button" :disabled="loadingMore" @click="loadMore">{{ loadingMore ? '加载中…' : '加载更多' }}</button></div>
      <FormMessage v-if="loadMoreError" :message="loadMoreError" />
    </div>
    <p v-else-if="data" class="empty-state">尚无审计记录。</p>
  </div>
</template>
