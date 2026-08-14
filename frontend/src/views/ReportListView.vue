<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { apiGet } from '@/api/client'
import type { WeeklyReport, WeeklyReportList } from '@/types/report'

const reports = ref<WeeklyReport[]>([])
const loading = ref(true)
const error = ref('')

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long' }).format(new Date(value)) : '—'
}

onMounted(async () => {
  try { reports.value = (await apiGet<WeeklyReportList>('/reports?limit=100')).items }
  catch (caught) { error.value = caught instanceof Error ? caught.message : '周报列表加载失败' }
  finally { loading.value = false }
})
</script>

<template>
  <div class="page-shell content-list-page">
    <header class="page-heading"><p class="section-kicker">TOURNAMENT ARCHIVE</p><h1>赛事周报</h1><p>按发布时间查看已完成赛事的最终排名、淘汰赛结果与四强卡组。</p></header>
    <nav class="center-tabs" aria-label="赛事中心内容"><RouterLink to="/tournaments">赛事</RouterLink><RouterLink to="/reports">周报</RouterLink></nav>
    <p v-if="loading" class="empty-state">正在加载周报…</p>
    <p v-else-if="error" class="form-message">{{ error }}</p>
    <div v-else-if="reports.length" class="report-list">
      <RouterLink v-for="item in reports" :key="item.id" :to="`/reports/${item.id}`" class="report-row">
        <span>{{ formatDate(item.published_at) }}</span><div><strong>{{ item.tournament_name }}</strong><small>{{ item.snapshot_content.tournament.participant_count }} 人 · {{ item.snapshot_content.tournament.swiss_rounds }} 轮瑞士 + Top {{ item.snapshot_content.tournament.playoff_size }}</small></div><i>→</i>
      </RouterLink>
    </div>
    <p v-else class="empty-state">暂无已发布周报。</p>
  </div>
</template>
