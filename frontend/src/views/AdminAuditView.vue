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
const formatTime = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value))

onMounted(() => apiGet<AuditLogListResponse>('/admin/audit-logs', undefined, authStore.token)
  .then((response) => { data.value = response })
  .catch((caught) => { error.value = caught instanceof Error ? caught.message : '审计日志加载失败' }))
</script>

<template>
  <div class="page-shell admin-page">
    <header class="page-heading"><p class="section-kicker">AUDIT TRAIL</p><h1>操作审计</h1><p>查看影响赛事公平性、审核结果和不可逆发布的关键操作。</p></header>
    <FormMessage v-if="error" :message="error" />
    <div v-if="data?.items.length" class="audit-list">
      <article v-for="item in data.items" :key="item.id" class="audit-row"><time>{{ formatTime(item.created_at) }}</time><div><strong>{{ auditActionText(item.action_type) }}</strong><p>{{ item.operator_nickname }} · {{ item.target_type }} / {{ item.target_id }}</p></div><details><summary>数据变化</summary><pre>{{ JSON.stringify({ before: item.before_json, after: item.after_json }, null, 2) }}</pre></details></article>
    </div>
    <p v-else-if="data" class="empty-state">尚无审计记录。</p>
  </div>
</template>
