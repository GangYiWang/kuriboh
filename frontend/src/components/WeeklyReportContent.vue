<script setup lang="ts">
import type { WeeklyReport } from '@/types/report'

defineProps<{ report: WeeklyReport }>()

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(value)) : '—'
}
</script>

<template>
  <article class="weekly-report-content">
    <header class="report-hero">
      <p class="section-kicker">WEEKLY REPORT</p>
      <h1>{{ report.snapshot_content.tournament.name }}</h1>
      <p>{{ formatDate(report.snapshot_content.tournament.competition_time) }} · {{ report.snapshot_content.tournament.participant_count }} 人参赛 · {{ report.snapshot_content.tournament.swiss_rounds }} 轮瑞士 + Top {{ report.snapshot_content.tournament.playoff_size }} · {{ report.snapshot_content.tournament.format }}</p>
    </header>

    <section class="report-section podium-section">
      <div class="section-title-row"><div><p class="section-kicker">FINAL STANDINGS</p><h2>最终四强与卡组</h2></div></div>
      <div class="podium-grid">
        <article v-for="item in report.snapshot_content.podium" :key="item.placement" class="podium-card">
          <div><span>{{ item.placement }}</span><strong>{{ item.nickname }}</strong><small>{{ item.placement === 1 ? '冠军' : item.placement === 2 ? '亚军' : '四强' }}</small></div>
          <img :src="item.image_url" :alt="`${item.nickname} 的卡组截图`" />
        </article>
      </div>
    </section>

    <section class="report-section">
      <p class="section-kicker">SWISS RANKING</p><h2>瑞士轮最终排名</h2>
      <div class="ranking-table-wrap"><table class="ranking-table"><thead><tr><th>排名</th><th>选手</th><th>胜负</th><th>OMW</th><th>败局小分</th></tr></thead><tbody><tr v-for="item in report.snapshot_content.swiss_rankings" :key="item.rank"><td>{{ item.rank }}</td><td>{{ item.nickname }}</td><td>{{ item.wins }}-{{ item.losses }}</td><td>{{ (item.omw * 100).toFixed(2) }}%</td><td>{{ item.loss_round_score }}</td></tr></tbody></table></div>
    </section>

    <section class="report-section">
      <p class="section-kicker">PLAYOFF RESULTS</p><h2>淘汰赛结果</h2>
      <div class="report-playoff-rounds">
        <section v-for="round in report.snapshot_content.playoff_rounds" :key="round.stage_no"><h3>{{ round.name }}</h3><article v-for="(match, index) in round.matches" :key="index"><span>#{{ match.seed_a }} {{ match.player_a }}</span><strong>{{ match.winner }} 胜</strong><span>#{{ match.seed_b }} {{ match.player_b }}</span></article></section>
      </div>
    </section>
  </article>
</template>
