<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { apiGet } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import type { MyTournament, MyTournamentListResponse } from '@/types/tournament'
import { registrationStatusText, tournamentStatusText } from '@/types/tournament'

const authStore = useAuthStore()
const data = ref<MyTournamentListResponse | null>(null)
const error = ref('')
const formatDate = (value: string | null) => value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(value)) : '时间待定'
const matchLabel = (item: MyTournament) => item.current_match
  ? `${item.current_match.stage === 'SWISS' ? `瑞士轮第 ${item.current_match.round_no} 轮` : '淘汰赛'} · 第 ${item.current_match.table_no} 桌`
  : '当前无进行中对阵'

onMounted(() => apiGet<MyTournamentListResponse>('/me/tournaments', undefined, authStore.token)
  .then((response) => { data.value = response })
  .catch((caught) => { error.value = caught instanceof Error ? caught.message : '赛事记录加载失败' }))
</script>

<template>
  <div class="page-shell content-list-page my-tournaments-page">
    <header class="page-heading"><p class="section-kicker">MY TOURNAMENTS</p><h1>我的赛事</h1><p>集中查看报名状态、当前对阵、正式排名和往期周报。</p></header>
    <FormMessage v-if="error" :message="error" />
    <div v-if="data?.items.length" class="my-tournament-list">
      <article v-for="item in data.items" :key="item.id" class="my-tournament-row">
        <header><span :class="['status-badge', `status-${item.status.toLowerCase()}`]">{{ tournamentStatusText[item.status] }}</span><small>{{ formatDate(item.planned_start_at) }}</small></header>
        <div class="my-tournament-main"><div><h2>{{ item.name }}</h2><p>报名：{{ registrationStatusText[item.registration_status] }}<template v-if="item.participant_status"> · {{ item.participant_status === 'WITHDRAWN' ? '已退赛' : '正式参赛' }}</template></p></div><RouterLink class="button secondary small" :to="`/tournaments/${item.id}`">进入赛事</RouterLink></div>
        <dl><div><dt>当前对阵</dt><dd>{{ matchLabel(item) }}</dd></div><div><dt>对手</dt><dd>{{ item.current_match?.opponent_nickname ?? '—' }}</dd></div><div><dt>正式排名</dt><dd>{{ item.ranking ? `第 ${item.ranking.rank} 名 · ${item.ranking.wins}-${item.ranking.losses}` : '—' }}</dd></div></dl>
        <RouterLink v-if="item.report_id" class="link-tone" :to="`/reports/${item.report_id}`">查看赛事周报 →</RouterLink>
      </article>
    </div>
    <div v-else-if="data" class="empty-content"><h2>还没有赛事记录</h2><p>前往赛事中心报名后，会在这里持续保留记录。</p><RouterLink class="button primary" to="/tournaments">浏览赛事</RouterLink></div>
  </div>
</template>
