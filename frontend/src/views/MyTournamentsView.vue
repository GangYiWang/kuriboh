<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { apiGet } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import type { MyTournament, MyTournamentListResponse, Tournament, TournamentListResponse } from '@/types/tournament'
import { registrationStatusText, tournamentStatusText } from '@/types/tournament'

const authStore = useAuthStore()
const route = useRoute()
const joined = ref<MyTournamentListResponse | null>(null)
const created = ref<TournamentListResponse | null>(null)
const error = ref('')
const tab = computed(() => route.query.tab === 'created' ? 'created' : 'joined')
const formatDate = (value: string | null) => value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(value)) : '时间待定'
const matchLabel = (item: MyTournament) => item.current_match
  ? `${item.current_match.stage === 'SWISS' ? `瑞士轮第 ${item.current_match.round_no} 轮` : '淘汰赛'} · 第 ${item.current_match.table_no} 桌`
  : '当前无进行中对阵'

async function loadCurrent() {
  error.value = ''
  try {
    if (tab.value === 'created' && !created.value) created.value = await apiGet<TournamentListResponse>('/me/created-tournaments?limit=100', undefined, authStore.token)
    if (tab.value === 'joined' && !joined.value) joined.value = await apiGet<MyTournamentListResponse>('/me/tournaments', undefined, authStore.token)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛事记录加载失败'
  }
}

watch(tab, loadCurrent)
onMounted(loadCurrent)
</script>

<template>
  <div class="page-shell content-list-page my-tournaments-page">
    <header class="page-heading split-heading"><div><p class="section-kicker">MY TOURNAMENTS</p><h1>我的赛事</h1><p>查看参加过的赛事，或继续管理自己发布的比赛。</p></div><RouterLink class="button primary" to="/tournaments/new">发布比赛</RouterLink></header>
    <nav class="center-tabs my-center-tabs" aria-label="我的赛事分类"><RouterLink :class="{ 'tab-selected': tab === 'joined' }" to="/my-tournaments">我参加的</RouterLink><RouterLink :class="{ 'tab-selected': tab === 'created' }" :to="{ path: '/my-tournaments', query: { tab: 'created' } }">我发布的</RouterLink></nav>
    <FormMessage v-if="error" :message="error" />

    <template v-if="tab === 'joined'">
      <div v-if="joined?.items.length" class="my-tournament-list">
        <article v-for="item in joined.items" :key="item.id" class="my-tournament-row">
          <header><span :class="['status-badge', `status-${item.status.toLowerCase()}`]">{{ tournamentStatusText[item.status] }}</span><small>{{ formatDate(item.planned_start_at) }}</small></header>
          <div class="my-tournament-main"><div><h2>{{ item.name }}</h2><p>报名：{{ registrationStatusText[item.registration_status] }}<template v-if="item.participant_status"> · {{ item.participant_status === 'WITHDRAWN' ? '已退赛' : '正式参赛' }}</template></p></div><RouterLink class="button secondary small" :to="`/tournaments/${item.id}`">进入赛事</RouterLink></div>
          <dl><div><dt>当前对阵</dt><dd>{{ matchLabel(item) }}</dd></div><div><dt>对手</dt><dd>{{ item.current_match?.opponent_nickname ?? '—' }}</dd></div><div><dt>正式排名</dt><dd>{{ item.ranking ? `第 ${item.ranking.rank} 名 · ${item.ranking.wins}-${item.ranking.losses}` : '—' }}</dd></div></dl>
          <RouterLink v-if="item.report_id" class="link-tone" :to="`/reports/${item.report_id}`">查看赛事周报 →</RouterLink>
        </article>
      </div>
      <div v-else-if="joined" class="empty-content"><h2>还没有参赛记录</h2><p>报名后，会在这里持续保留记录。</p><RouterLink class="button primary" to="/tournaments">浏览赛事</RouterLink></div>
    </template>

    <template v-else>
      <div v-if="created?.items.length" class="admin-tournament-list created-tournament-list">
        <article v-for="item in created.items" :key="item.id" class="admin-tournament-row">
          <div><span :class="['status-badge', `status-${item.status.toLowerCase()}`]">{{ tournamentStatusText[item.status] }}</span><strong>{{ item.name }}</strong><small>{{ formatDate(item.planned_start_at) }} · 比赛码 <b class="tournament-code">{{ item.code }}</b></small></div>
          <div class="row-actions"><RouterLink class="button secondary small" :to="`/tournaments/${item.id}`">查看</RouterLink><RouterLink class="button primary small" :to="`/tournaments/${item.id}/manage/settings`">管理</RouterLink></div>
        </article>
      </div>
      <div v-else-if="created" class="empty-content"><h2>还没有发布比赛</h2><p>任何登录账号都可以创建比赛并参与其他比赛。</p><RouterLink class="button primary" to="/tournaments/new">发布第一场比赛</RouterLink></div>
    </template>
  </div>
</template>
