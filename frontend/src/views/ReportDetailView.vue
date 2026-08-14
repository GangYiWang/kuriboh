<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { apiGet } from '@/api/client'
import WeeklyReportContent from '@/components/WeeklyReportContent.vue'
import type { WeeklyReport } from '@/types/report'

const route = useRoute()
const report = ref<WeeklyReport | null>(null)
const error = ref('')
onMounted(async () => {
  try { report.value = await apiGet<WeeklyReport>(`/reports/${String(route.params.id)}`) }
  catch (caught) { error.value = caught instanceof Error ? caught.message : '周报加载失败' }
})
</script>

<template>
  <div class="page-shell report-detail-page">
    <RouterLink class="back-link" to="/reports">← 返回赛事周报</RouterLink>
    <WeeklyReportContent v-if="report" :report="report" />
    <p v-else-if="error" class="form-message">{{ error }}</p>
    <p v-else class="empty-state">正在加载周报…</p>
  </div>
</template>
