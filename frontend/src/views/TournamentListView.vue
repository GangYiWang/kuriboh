<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { apiGet } from '@/api/client'
import type { Tournament, TournamentListResponse } from '@/types/tournament'
import { tournamentStatusText } from '@/types/tournament'

const tournaments = ref<Tournament[]>([])
const loading = ref(true)
const error = ref('')
const search = ref('')

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  return term ? tournaments.value.filter((item) => item.name.toLowerCase().includes(term)) : tournaments.value
})

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '待定'
}

onMounted(async () => {
  try {
    tournaments.value = (await apiGet<TournamentListResponse>('/tournaments?limit=100')).items
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛事列表加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-shell content-list-page">
    <header class="page-heading split-heading">
      <div>
        <p class="section-kicker">TOURNAMENT CENTER</p>
        <h1>赛事中心</h1>
        <p>统一查看报名中、进行中与往期的栗子杯赛事。</p>
      </div>
      <label class="list-search"><span class="visually-hidden">搜索赛事</span><input v-model="search" type="search" placeholder="搜索赛事名称" /></label>
    </header>
    <nav class="center-tabs" aria-label="赛事中心内容"><RouterLink to="/tournaments">赛事</RouterLink><RouterLink to="/reports">周报</RouterLink></nav>
    <p v-if="loading" class="empty-state">正在加载赛事…</p>
    <p v-else-if="error" class="form-message">{{ error }}</p>
    <div v-else-if="filtered.length" class="tournament-list">
      <RouterLink v-for="item in filtered" :key="item.id" class="tournament-row" :to="`/tournaments/${item.id}`">
        <span :class="['status-badge', `status-${item.status.toLowerCase()}`]">{{ tournamentStatusText[item.status] }}</span>
        <div class="tournament-summary">
          <strong>{{ item.name }}</strong>
          <span>{{ formatDate(item.planned_start_at) }}</span>
        </div>
        <dl class="tournament-facts">
          <div><dt>{{ item.status === 'REGISTRATION' ? '已通过' : '参赛人数' }}</dt><dd>{{ item.approved_count }} / {{ item.max_players ?? '—' }}</dd></div>
          <div><dt>赛制</dt><dd>{{ item.swiss_rounds ?? '—' }} 轮瑞士 + Top {{ item.playoff_size ?? '—' }}</dd></div>
          <div><dt>禁卡表</dt><dd>{{ item.banlist_version ?? '待定' }}</dd></div>
        </dl>
        <span class="row-arrow">→</span>
      </RouterLink>
    </div>
    <p v-else class="empty-state">暂无符合条件的已发布赛事。</p>
  </div>
</template>
