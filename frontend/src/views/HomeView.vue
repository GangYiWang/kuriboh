<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { apiGet } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { Announcement, ListResponse } from '@/types/content'
import type { MyTournamentListResponse } from '@/types/tournament'
import { tournamentStatusText } from '@/types/tournament'

const authStore = useAuthStore()
const announcement = ref<Announcement | null>(null)
const myTournaments = ref<MyTournamentListResponse | null>(null)
const currentTournament = computed(() => myTournaments.value?.items.find((item) => item.status !== 'ENDED' && item.registration_status === 'APPROVED') ?? null)

onMounted(async () => {
  const announcements = await apiGet<ListResponse<Announcement>>('/announcements?limit=1').catch(() => null)
  announcement.value = announcements?.items.find((item) => item.is_pinned) ?? null
  await authStore.ensureProfile()
  if (authStore.token) {
    myTournaments.value = await apiGet<MyTournamentListResponse>('/me/tournaments', undefined, authStore.token).catch(() => null)
  }
})
</script>

<template>
  <div class="page-shell">
    <section class="hero">
      <div class="hero-copy">
        <h1>每一场认真对局，<br /><span>都值得被好好记录。</span></h1>
        <p class="hero-description">
          从报名、瑞士轮到淘汰赛，一站完成栗子杯的参赛与追踪。规则清晰，赛程透明。
        </p>
        <div class="hero-actions">
          <RouterLink class="button primary" to="/tournaments">浏览赛事</RouterLink>
          <RouterLink class="button secondary" to="/rules">查看比赛规则</RouterLink>
        </div>
      </div>

      <div class="hero-emblem" aria-hidden="true">
        <span class="emblem-ring ring-one" />
        <span class="emblem-ring ring-two" />
        <div class="emblem-core">
          <span class="core-seed" />
          <small>KURIBOH CUP</small>
        </div>
        <span class="orbit-label label-a">SWISS</span>
        <span class="orbit-label label-b">TOP N</span>
        <span class="orbit-label label-c">BO1</span>
      </div>
    </section>

    <RouterLink v-if="announcement" :to="`/announcements/${announcement.id}`" class="pinned-announcement">
      <span>置顶公告</span><strong>{{ announcement.title }}</strong><i>查看详情 →</i>
    </RouterLink>

    <section v-if="currentTournament" class="current-tournament-panel" aria-labelledby="current-tournament-title">
      <div class="section-heading"><div><h2 id="current-tournament-title">我的当前赛事</h2></div><span :class="['status-badge', `status-${currentTournament.status.toLowerCase()}`]">{{ tournamentStatusText[currentTournament.status] }}</span></div>
      <div class="current-tournament-main"><div><h3>{{ currentTournament.name }}</h3><p v-if="currentTournament.current_match">{{ currentTournament.current_match.stage === 'SWISS' ? `瑞士轮第 ${currentTournament.current_match.round_no} 轮` : '淘汰赛' }} · 第 {{ currentTournament.current_match.table_no }} 桌 · 对手 {{ currentTournament.current_match.opponent_nickname }}</p><p v-else>当前没有进行中的个人对阵。</p></div><RouterLink class="button primary" :to="`/tournaments/${currentTournament.id}`">进入赛事</RouterLink></div>
      <dl><div><dt>当前排名</dt><dd>{{ currentTournament.ranking ? `第 ${currentTournament.ranking.rank} 名` : '—' }}</dd></div><div><dt>当前战绩</dt><dd>{{ currentTournament.ranking ? `${currentTournament.ranking.wins}-${currentTournament.ranking.losses}` : '—' }}</dd></div></dl>
    </section>

    <section class="quick-section" aria-labelledby="quick-title">
      <div class="section-heading">
        <div>
          <h2 id="quick-title">基础入口</h2>
        </div>
      </div>
      <div class="quick-links">
        <RouterLink to="/tournaments"><span>01</span><strong>赛事中心</strong><small>浏览赛事并提交报名</small><i>→</i></RouterLink>
        <RouterLink to="/rules"><span>02</span><strong>比赛规则</strong><small>了解栗子杯赛制与流程</small><i>→</i></RouterLink>
        <RouterLink to="/banlists"><span>03</span><strong>当前禁卡表</strong><small>查看当前版本与永久历史</small><i>→</i></RouterLink>
        <RouterLink to="/my-tournaments"><span>04</span><strong>我的赛事</strong><small>登录后查看参赛记录</small><i>→</i></RouterLink>
      </div>
    </section>
  </div>
</template>
