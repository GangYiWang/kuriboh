<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiGet } from '@/api/client'
import TournamentAreaNav from '@/components/TournamentAreaNav.vue'
import { useAuthStore } from '@/stores/auth'
import type { Tournament, TournamentListResponse } from '@/types/tournament'
import { tournamentStatusText } from '@/types/tournament'

const tournaments = ref<Tournament[]>([])
const authStore = useAuthStore()
const router = useRouter()
const loading = ref(true)
const error = ref('')
const code = ref('')
const nameQuery = ref('')
const searchMode = ref<'code' | 'name' | null>(null)
const searchBusy = ref(false)
const searchError = ref('')

async function loadTournaments(search?: string) {
  const query = search ? `&search=${encodeURIComponent(search)}` : ''
  tournaments.value = (await apiGet<TournamentListResponse>(`/tournaments?limit=100${query}`)).items
}

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '待定'
}

async function findByCode() {
  const normalized = code.value.trim().toUpperCase()
  if (!/^[A-Z0-9]{6}$/.test(normalized)) {
    searchError.value = '请输入 6 位大写字母或数字组成的比赛码'
    return
  }
  searchBusy.value = true
  searchError.value = ''
  try {
    const item = await apiGet<Tournament>(`/tournaments/code/${normalized}`)
    await router.push(`/tournaments/${item.id}`)
  } catch (caught) {
    searchError.value = caught instanceof Error ? caught.message : '未找到该比赛'
  } finally {
    searchBusy.value = false
  }
}

async function findByName() {
  const query = nameQuery.value.trim()
  if (!query) {
    searchError.value = '请输入赛事名称'
    return
  }
  searchBusy.value = true
  searchError.value = ''
  error.value = ''
  try {
    await loadTournaments(query)
  } catch (caught) {
    searchError.value = caught instanceof Error ? caught.message : '赛事名称查找失败'
  } finally {
    searchBusy.value = false
  }
}

function openSearch(mode: 'code' | 'name') {
  searchMode.value = mode
  searchError.value = ''
}

async function cancelSearch() {
  searchMode.value = null
  searchError.value = ''
  code.value = ''
  nameQuery.value = ''
  try {
    await loadTournaments()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛事列表加载失败'
  }
}

async function publish() {
  await router.push(authStore.isAuthenticated
    ? '/tournaments/new'
    : { path: '/login', query: { redirect: '/tournaments/new' } })
}

onMounted(async () => {
  try {
    await loadTournaments()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛事列表加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-shell content-list-page">
    <header class="page-heading split-heading tournament-area-heading">
      <div>
        <h1>赛事中心</h1>
        <p>统一查看报名中、进行中与往期的栗子杯赛事。</p>
      </div>
      <button class="button primary" type="button" @click="publish">发布比赛</button>
    </header>
    <TournamentAreaNav show-competition-tabs />
    <div class="tournament-filter-bar">
      <button class="button secondary" type="button" :aria-expanded="searchMode === 'code'" @click="openSearch('code')">按比赛码查找</button>
      <button class="button secondary" type="button" :aria-expanded="searchMode === 'name'" @click="openSearch('name')">按赛事名称查找</button>
    </div>
    <form v-if="searchMode === 'code'" class="tournament-search-panel" @submit.prevent="findByCode"><label><span>按比赛码查找</span><input v-model="code" class="code-search-input" maxlength="6" autocomplete="off" placeholder="例如 FU6Q8W" @input="code = code.toUpperCase()" /></label><button class="button primary" type="submit" :disabled="searchBusy">{{ searchBusy ? '查找中…' : '查找比赛' }}</button><button class="button secondary" type="button" :disabled="searchBusy" @click="cancelSearch">取消</button><p v-if="searchError" class="form-message">{{ searchError }}</p></form>
    <form v-if="searchMode === 'name'" class="tournament-search-panel" @submit.prevent="findByName"><label><span>按赛事名称查找</span><input v-model="nameQuery" autocomplete="off" placeholder="输入赛事名称" /></label><button class="button primary" type="submit" :disabled="searchBusy">{{ searchBusy ? '查找中…' : '查找赛事' }}</button><button class="button secondary" type="button" :disabled="searchBusy" @click="cancelSearch">取消</button><p v-if="searchError" class="form-message">{{ searchError }}</p></form>
    <p v-if="loading" class="empty-state">正在加载赛事…</p>
    <p v-else-if="error" class="form-message">{{ error }}</p>
    <div v-else-if="tournaments.length" class="tournament-list">
      <RouterLink v-for="item in tournaments" :key="item.id" class="tournament-row" :to="`/tournaments/${item.id}`">
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
