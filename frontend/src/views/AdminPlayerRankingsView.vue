<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { apiGet } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import type { AdminPlayerRankingListResponse } from '@/types/statistics'

const authStore = useAuthStore()
const rankings = ref<AdminPlayerRankingListResponse | null>(null)
const searchInput = ref('')
const activeSearch = ref('')
const expandedPlayerId = ref<string | null>(null)
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const loadMoreError = ref('')
const percentFormatter = new Intl.NumberFormat('zh-CN', {
  style: 'percent',
  maximumFractionDigits: 2,
})

function rankingPath(offset: number): string {
  const params = new URLSearchParams({ offset: String(offset), limit: '20' })
  if (activeSearch.value) params.set('search', activeSearch.value)
  return `/admin/player-rankings?${params.toString()}`
}

async function loadRankings(append = false): Promise<void> {
  const offset = append ? rankings.value?.items.length ?? 0 : 0
  const response = await apiGet<AdminPlayerRankingListResponse>(
    rankingPath(offset),
    undefined,
    authStore.token,
  )
  rankings.value = append && rankings.value
    ? { items: [...rankings.value.items, ...response.items], total: response.total }
    : response
}

async function searchRankings(): Promise<void> {
  loading.value = true
  error.value = ''
  loadMoreError.value = ''
  expandedPlayerId.value = null
  activeSearch.value = searchInput.value.trim()
  try {
    await loadRankings()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '积分排名加载失败'
  } finally {
    loading.value = false
  }
}

async function clearSearch(): Promise<void> {
  searchInput.value = ''
  await searchRankings()
}

async function loadMore(): Promise<void> {
  loadingMore.value = true
  loadMoreError.value = ''
  try {
    await loadRankings(true)
  } catch (caught) {
    loadMoreError.value = caught instanceof Error ? caught.message : '更多积分排名加载失败'
  } finally {
    loadingMore.value = false
  }
}

function toggleDetails(userId: string): void {
  expandedPlayerId.value = expandedPlayerId.value === userId ? null : userId
}

function formatWinRate(value: number): string {
  return percentFormatter.format(value)
}

onMounted(() => {
  void searchRankings()
})
</script>

<template>
  <div class="page-shell admin-page player-rankings-page">
    <header class="page-heading">
      <p class="section-kicker">PLAYER RANKINGS</p>
      <h1>积分排名</h1>
      <p>查看所有注册人员在已结束赛事中的累计积分与成绩。</p>
    </header>

    <form class="player-ranking-search" role="search" @submit.prevent="searchRankings">
      <label class="visually-hidden" for="player-ranking-search-input">搜索玩家昵称</label>
      <input
        id="player-ranking-search-input"
        v-model="searchInput"
        type="search"
        maxlength="50"
        placeholder="搜索玩家昵称"
      />
      <button class="button secondary" type="submit" :disabled="loading">搜索</button>
      <button v-if="activeSearch" class="button secondary" type="button" :disabled="loading" @click="clearSearch">清除</button>
    </form>

    <FormMessage v-if="error" :message="error" />
    <p v-if="loading && !rankings" class="empty-state">正在加载积分排名…</p>

    <section v-else-if="rankings" class="player-ranking-section" aria-labelledby="player-ranking-table-title">
      <div class="player-ranking-heading">
        <h2 id="player-ranking-table-title">全部人员</h2>
        <span>共 {{ rankings.total }} 人</span>
      </div>

      <div v-if="rankings.items.length" class="player-ranking-table-wrap">
        <table class="player-ranking-table">
          <colgroup>
            <col class="player-ranking-col-rank" />
            <col class="player-ranking-col-name" />
            <col class="player-ranking-col-champions" />
            <col class="player-ranking-col-points" />
            <col class="player-ranking-col-action" />
          </colgroup>
          <thead>
            <tr><th>排名</th><th>玩家昵称</th><th>冠军数</th><th>积分</th><th>操作</th></tr>
          </thead>
          <tbody>
            <template v-for="item in rankings.items" :key="item.user_id">
              <tr :class="{ 'player-ranking-row-expanded': expandedPlayerId === item.user_id }">
                <td class="player-ranking-rank">{{ item.rank }}</td>
                <td class="player-ranking-name">{{ item.nickname }}</td>
                <td>{{ item.champion_count }}</td>
                <td class="player-ranking-points">{{ item.total_points }}</td>
                <td>
                  <button
                    class="player-ranking-detail-button"
                    type="button"
                    :aria-expanded="expandedPlayerId === item.user_id"
                    :aria-controls="`player-ranking-details-${item.user_id}`"
                    @click="toggleDetails(item.user_id)"
                  >{{ expandedPlayerId === item.user_id ? '收起' : '详情' }}</button>
                </td>
              </tr>
              <tr v-if="expandedPlayerId === item.user_id" :id="`player-ranking-details-${item.user_id}`" class="player-ranking-detail-row">
                <td colspan="5">
                  <dl class="player-ranking-details">
                    <div><dt>参赛次数</dt><dd>{{ item.tournament_count }}</dd></div>
                    <div><dt>亚军</dt><dd>{{ item.runner_up_count }}</dd></div>
                    <div><dt>晋级四强</dt><dd>{{ item.top_4_count }}</dd></div>
                    <div><dt>晋级八强</dt><dd>{{ item.top_8_count }}</dd></div>
                    <div><dt>总战绩</dt><dd>{{ item.total_wins }} 胜 {{ item.total_losses }} 负</dd></div>
                    <div><dt>胜率</dt><dd>{{ formatWinRate(item.win_rate) }}</dd></div>
                    <div><dt>轮空次数</dt><dd>{{ item.total_byes }}</dd></div>
                  </dl>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <p v-else class="empty-state">{{ activeSearch ? '没有找到匹配的玩家。' : '暂无注册人员。' }}</p>

      <div v-if="rankings.items.length < rankings.total" class="form-actions tournament-load-more">
        <button class="button secondary" type="button" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? '加载中…' : '加载更多' }}
        </button>
      </div>
      <FormMessage v-if="loadMoreError" :message="loadMoreError" />
    </section>
  </div>
</template>
