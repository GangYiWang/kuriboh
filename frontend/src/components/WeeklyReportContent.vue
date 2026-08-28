<script setup lang="ts">
import type { WeeklyReport } from '@/types/report'
import { deckPlacementText } from '@/types/report'

defineProps<{ report: WeeklyReport }>()

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(value)) : '—'
}
</script>

<template>
  <article class="weekly-report-content">
    <header class="report-hero">
      <h1>{{ report.snapshot_content.tournament.name }}</h1>
      <p>{{ formatDate(report.snapshot_content.tournament.competition_time) }} · {{ report.snapshot_content.tournament.participant_count }} 人参赛 · {{ report.snapshot_content.tournament.swiss_rounds }} 轮瑞士 + Top {{ report.snapshot_content.tournament.playoff_size }} · {{ report.snapshot_content.tournament.format }}</p>
    </header>

    <section class="report-section podium-section">
      <div class="section-title-row"><div><h2>最终四强与卡组</h2></div></div>
      <div class="podium-grid">
        <article v-for="item in report.snapshot_content.podium" :key="item.placement" class="podium-card">
          <div><span>{{ deckPlacementText(item.placement) }}</span><strong>{{ item.nickname }}</strong></div>
          <img :src="item.image_url" :alt="`${item.nickname} 的卡组截图`" />
        </article>
      </div>
    </section>
  </article>
</template>
