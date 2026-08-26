<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { apiGet, apiPost } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import SwissLivePanel from '@/components/SwissLivePanel.vue'
import PlayoffBracket from '@/components/PlayoffBracket.vue'
import DeckSubmissionPanel from '@/components/DeckSubmissionPanel.vue'
import { useAuthStore } from '@/stores/auth'
import type { Registration, Tournament } from '@/types/tournament'
import { registrationStatusText, tournamentStatusText } from '@/types/tournament'

const route = useRoute()
const authStore = useAuthStore()
const tournament = ref<Tournament | null>(null)
const registration = ref<Registration | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const message = ref('')
const activeTab = ref<'info' | 'matches' | 'results' | 'deck'>('info')
const resultsStage = ref<'swiss' | 'playoff'>('swiss')
const tournamentId = computed(() => String(route.params.id))
const remaining = computed(() => Math.max(0, (tournament.value?.max_players ?? 0) - (tournament.value?.approved_count ?? 0)))
const canReapply = computed(() => registration.value?.status === 'CANCELED' && !registration.value.reviewed_by_id)

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(value)) : '待定'
}

async function load() {
  tournament.value = await apiGet<Tournament>(`/tournaments/${tournamentId.value}`)
  resultsStage.value = ['ELIMINATION', 'ENDED'].includes(tournament.value.status) ? 'playoff' : 'swiss'
  if (authStore.token) {
    registration.value = await apiGet<Registration>(
      `/tournaments/${tournamentId.value}/registrations/me`, undefined, authStore.token,
    ).catch(() => null)
  }
}

async function apply() {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    registration.value = await apiPost<Registration>(`/tournaments/${tournamentId.value}/registrations`, {
      nickname_matches_game: true,
      accepts_rules: true,
    }, authStore.token)
    message.value = '报名已提交，等待赛事主办方审核。'
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '报名提交失败'
  } finally {
    busy.value = false
  }
}

async function cancelRegistration() {
  busy.value = true
  error.value = ''
  try {
    registration.value = await apiPost<Registration>(
      `/tournaments/${tournamentId.value}/registrations/cancel`, {}, authStore.token,
    )
    message.value = '报名已取消。'
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '取消报名失败'
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  try {
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛事加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-if="loading" class="page-shell empty-state">正在加载赛事…</div>
  <div v-else-if="tournament" class="tournament-detail-page">
    <header class="detail-banner">
      <div class="page-shell detail-banner-inner">
        <RouterLink class="back-link" to="/tournaments">← 返回赛事中心</RouterLink>
        <span :class="['status-badge', `status-${tournament.status.toLowerCase()}`]">{{ tournamentStatusText[tournament.status] }}</span>
        <h1>{{ tournament.name }}</h1>
        <RouterLink v-if="authStore.user?.id === tournament.created_by_id" class="button secondary" :to="`/tournaments/${tournament.id}/manage/settings`">管理比赛</RouterLink>
      </div>
    </header>
    <div :class="['page-shell', 'tournament-detail-layout', { 'tournament-detail-layout-results': ['results', 'deck'].includes(activeTab) }]">
      <nav class="tournament-detail-tabs" aria-label="赛事页面内容">
        <button type="button" :class="{ active: activeTab === 'info' }" :aria-current="activeTab === 'info' ? 'page' : undefined" @click="activeTab = 'info'">赛事信息</button>
        <button type="button" :class="{ active: activeTab === 'matches' }" :aria-current="activeTab === 'matches' ? 'page' : undefined" @click="activeTab = 'matches'">对阵</button>
        <button type="button" :class="{ active: activeTab === 'results' }" :aria-current="activeTab === 'results' ? 'page' : undefined" @click="activeTab = 'results'">赛果</button>
        <button v-if="tournament.status === 'ENDED' && authStore.isAuthenticated && authStore.token" type="button" :class="{ active: activeTab === 'deck' }" :aria-current="activeTab === 'deck' ? 'page' : undefined" @click="activeTab = 'deck'">卡组</button>
      </nav>
      <main>
        <section v-if="activeTab === 'info'" class="info-section">
          <h2>赛事信息</h2>
          <dl class="info-grid">
            <div><dt>预计开赛时间</dt><dd>{{ formatDate(tournament.planned_start_at) }}</dd></div>
            <div><dt>比赛码</dt><dd class="tournament-code">{{ tournament.code ?? '—' }}</dd></div>
            <div><dt>报名情况</dt><dd>{{ tournament.approved_count }} / {{ tournament.max_players }} 人</dd></div>
            <div><dt>瑞士轮轮数</dt><dd>{{ tournament.swiss_rounds }} 轮</dd></div>
            <div><dt>淘汰赛晋级</dt><dd>Top {{ tournament.playoff_size }}</dd></div>
            <div><dt>禁卡表版本</dt><dd><RouterLink v-if="tournament.banlist_version_id" class="link-tone" :to="`/banlists/${tournament.banlist_version_id}`">{{ tournament.banlist_version }} ↗</RouterLink></dd></div>
          </dl>
          <section class="tournament-description" aria-labelledby="tournament-description-title">
            <h3 id="tournament-description-title">赛事说明</h3>
            <p class="long-copy">{{ tournament.description || '暂无赛事说明。' }}</p>
          </section>
        </section>
        <SwissLivePanel
          v-if="activeTab === 'matches' && tournament.status === 'SWISS'"
          :tournament-id="tournament.id"
          :token="authStore.token"
          :is-player="authStore.isAuthenticated"
          view="matches"
        />
        <PlayoffBracket
          v-if="activeTab === 'matches' && ['ELIMINATION', 'ENDED'].includes(tournament.status)"
          :tournament-id="tournament.id"
          :token="authStore.token"
          :is-player="authStore.isAuthenticated"
          view="matches"
        />
        <section v-if="activeTab === 'matches' && ['DRAFT', 'REGISTRATION'].includes(tournament.status)" class="tournament-stage-empty">
          <h2>对阵</h2><p class="empty-state compact">赛事开始并发布首轮后显示对阵。</p>
        </section>
        <section v-if="activeTab === 'results' && ['SWISS', 'ELIMINATION', 'ENDED'].includes(tournament.status)" class="public-results-view">
          <header class="swiss-progress-heading"><div><h2>赛果</h2></div></header>
          <nav class="competition-stage-tabs" role="tablist" aria-label="赛果阶段">
            <button type="button" role="tab" :class="{ active: resultsStage === 'swiss' }" :aria-selected="resultsStage === 'swiss'" @click="resultsStage = 'swiss'">瑞士轮</button>
            <button type="button" role="tab" :class="{ active: resultsStage === 'playoff' }" :aria-selected="resultsStage === 'playoff'" @click="resultsStage = 'playoff'">淘汰赛</button>
          </nav>
          <div role="tabpanel" class="public-results-panel">
            <SwissLivePanel
              v-if="resultsStage === 'swiss'"
              :tournament-id="tournament.id"
              :token="authStore.token"
              :is-player="authStore.isAuthenticated"
              view="results"
              embedded
            />
            <PlayoffBracket
              v-else
              :tournament-id="tournament.id"
              :token="authStore.token"
              :is-player="authStore.isAuthenticated"
              view="results"
              embedded
            />
          </div>
        </section>
        <section v-else-if="activeTab === 'results'" class="tournament-stage-empty">
          <h2>赛果</h2><p class="empty-state compact">赛事开始后显示排名与赛果。</p>
        </section>
        <DeckSubmissionPanel
          v-if="activeTab === 'deck' && tournament.status === 'ENDED' && authStore.token"
          :tournament-id="tournament.id"
          :token="authStore.token"
        />
      </main>
      <aside v-if="activeTab === 'matches'" aria-hidden="true" />
      <aside v-else-if="activeTab === 'info'" class="signup-box">
        <h2>赛事报名</h2>
        <FormMessage v-if="message" type="success" :message="message" />
        <FormMessage v-if="error" :message="error" />
        <template v-if="tournament.status === 'REGISTRATION'">
          <div class="capacity-copy"><span>已通过 {{ tournament.approved_count }} 人</span><strong>剩余 {{ remaining }} 席</strong></div>
          <div class="capacity-track"><i :style="{ width: `${Math.min(100, tournament.approved_count / (tournament.max_players || 1) * 100)}%` }" /></div>
          <template v-if="registration">
            <p>当前报名状态：<strong>{{ registrationStatusText[registration.status] }}</strong></p>
            <button v-if="['PENDING', 'APPROVED'].includes(registration.status)" class="button secondary full" type="button" :disabled="busy" @click="cancelRegistration">取消报名</button>
            <button v-else-if="canReapply" class="button primary full" type="button" :disabled="busy || remaining === 0" @click="apply">重新报名</button>
            <small v-else>主办方拒绝或取消的报名只能由主办方恢复。</small>
          </template>
          <template v-else-if="authStore.isAuthenticated">
            <button class="button primary full" type="button" :disabled="busy || remaining === 0" @click="apply">确认报名</button>
          </template>
          <RouterLink v-else class="button primary full" :to="{ path: '/login', query: { redirect: route.fullPath } }">登录后报名</RouterLink>
        </template>
        <template v-else>
          <p>赛事已开始，报名现已关闭。</p>
          <p v-if="tournament.status === 'ENDED'" class="form-hint">赛事结果已经永久锁定。最终四强可在“卡组”中上传卡组截图。</p>
        </template>
      </aside>
    </div>
  </div>
  <div v-else class="page-shell empty-state"><p class="form-message">{{ error }}</p></div>
</template>
