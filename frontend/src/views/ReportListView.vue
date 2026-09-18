<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { apiGet } from '@/api/client'
import TournamentAreaNav from '@/components/TournamentAreaNav.vue'
import type { WeeklyReport, WeeklyReportList } from '@/types/report'

const reports = ref<WeeklyReport[]>([])
const total = ref(0)
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')
const loadMoreError = ref('')

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long' }).format(new Date(value)) : '—'
}

async function loadReports(append = false) {
  const offset = append ? reports.value.length : 0
  const response = await apiGet<WeeklyReportList>(`/reports?offset=${offset}&limit=10`)
  reports.value = append ? [...reports.value, ...response.items] : response.items
  total.value = response.total
}

async function loadMore() {
  loadingMore.value = true
  loadMoreError.value = ''
  try {
    await loadReports(true)
  } catch (caught) {
    loadMoreError.value = caught instanceof Error ? caught.message : '更多周报加载失败'
  } finally {
    loadingMore.value = false
  }
}

onMounted(async () => {
  try { await loadReports() }
  catch (caught) { error.value = caught instanceof Error ? caught.message : '周报列表加载失败' }
  finally { loading.value = false }
})
</script>

<template>
  <div class="page-shell content-list-page">
    <header class="page-heading tournament-area-heading"><p class="section-kicker">TOURNAMENT CENTER</p><h1>赛事中心</h1><p>按发布时间查看已完成赛事的赛事概要与四强卡组。</p></header>
    <TournamentAreaNav />
    <p v-if="loading" class="empty-state">正在加载周报…</p>
    <p v-else-if="error" class="form-message">{{ error }}</p>
    <div v-else-if="reports.length" class="report-list">
      <RouterLink v-for="item in reports" :key="item.id" :to="`/reports/${item.id}`" class="report-row">
        <span>{{ formatDate(item.published_at) }}</span><div><strong>{{ item.tournament_name }}</strong><small>{{ item.snapshot_content.tournament.participant_count }} 人 · {{ item.snapshot_content.tournament.swiss_rounds }} 轮瑞士 + Top {{ item.snapshot_content.tournament.playoff_size }}</small></div><i>→</i>
      </RouterLink>
      <div v-if="reports.length < total" class="form-actions tournament-load-more"><button class="button secondary" type="button" :disabled="loadingMore" @click="loadMore">{{ loadingMore ? '加载中…' : '加载更多' }}</button></div>
      <p v-if="loadMoreError" class="form-message">{{ loadMoreError }}</p>
    </div>
    <p v-else class="empty-state">暂无已发布周报。</p>
  </div>
</template>
