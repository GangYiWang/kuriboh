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
const accepted = ref(false)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const message = ref('')
const tournamentId = computed(() => String(route.params.id))
const remaining = computed(() => Math.max(0, (tournament.value?.max_players ?? 0) - (tournament.value?.approved_count ?? 0)))

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long', timeStyle: 'short' }).format(new Date(value)) : '待定'
}

async function load() {
  tournament.value = await apiGet<Tournament>(`/tournaments/${tournamentId.value}`)
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
      nickname_matches_game: accepted.value,
      accepts_rules: accepted.value,
    }, authStore.token)
    message.value = '报名已提交，等待管理员审核。'
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
        <p>{{ tournament.description || '暂无赛事说明。' }}</p>
      </div>
    </header>
    <div class="page-shell tournament-detail-layout">
      <main>
        <section class="info-section">
          <p class="section-kicker">TOURNAMENT INFO</p>
          <h2>赛事信息</h2>
          <dl class="info-grid">
            <div><dt>预计开赛时间</dt><dd>{{ formatDate(tournament.planned_start_at) }}</dd></div>
            <div><dt>报名情况</dt><dd>{{ tournament.approved_count }} / {{ tournament.max_players }} 人</dd></div>
            <div><dt>瑞士轮轮数</dt><dd>{{ tournament.swiss_rounds }} 轮</dd></div>
            <div><dt>淘汰赛晋级</dt><dd>Top {{ tournament.playoff_size }}</dd></div>
            <div><dt>比赛局制</dt><dd>BO1</dd></div>
            <div><dt>禁卡表版本</dt><dd><RouterLink v-if="tournament.banlist_version_id" class="link-tone" :to="`/banlists/${tournament.banlist_version_id}`">{{ tournament.banlist_version }} ↗</RouterLink></dd></div>
          </dl>
        </section>
        <section class="info-section">
          <p class="section-kicker">RULE SUMMARY</p>
          <h2>比赛说明</h2>
          <p class="long-copy">固定采用瑞士轮加单淘汰赛。预计时间只作提示，赛事由管理员手动开始；开始后不会自动生成第 1 轮。</p>
          <div class="rule-notes"><span>无平局</span><span>BO1</span><span>开赛后关闭报名</span></div>
        </section>
        <SwissLivePanel
          v-if="tournament.status === 'SWISS'"
          :tournament-id="tournament.id"
          :token="authStore.token"
          :is-player="authStore.user?.role === 'PLAYER'"
        />
        <PlayoffBracket
          v-if="['ELIMINATION', 'ENDED'].includes(tournament.status)"
          :tournament-id="tournament.id"
          :token="authStore.token"
          :is-player="authStore.user?.role === 'PLAYER'"
        />
        <DeckSubmissionPanel
          v-if="tournament.status === 'ENDED' && authStore.user?.role === 'PLAYER' && authStore.token"
          :tournament-id="tournament.id"
          :token="authStore.token"
        />
      </main>
      <aside class="signup-box">
        <p class="section-kicker">REGISTRATION</p>
        <h2>赛事报名</h2>
        <FormMessage v-if="message" type="success" :message="message" />
        <FormMessage v-if="error" :message="error" />
        <template v-if="tournament.status === 'REGISTRATION'">
          <div class="capacity-copy"><span>已通过 {{ tournament.approved_count }} 人</span><strong>剩余 {{ remaining }} 席</strong></div>
          <div class="capacity-track"><i :style="{ width: `${Math.min(100, tournament.approved_count / (tournament.max_players || 1) * 100)}%` }" /></div>
          <template v-if="registration">
            <p>当前报名状态：<strong>{{ registrationStatusText[registration.status] }}</strong></p>
            <button v-if="['PENDING', 'APPROVED'].includes(registration.status)" class="button secondary full" type="button" :disabled="busy" @click="cancelRegistration">取消报名</button>
            <small>已拒绝或取消的报名只能由管理员恢复。</small>
          </template>
          <template v-else-if="authStore.user?.role === 'PLAYER'">
            <label class="check-row"><input v-model="accepted" type="checkbox" /><span>我确认 Master Duel 游戏内昵称与网站昵称一致，并同意赛事规则</span></label>
            <button class="button primary full" type="button" :disabled="busy || !accepted || remaining === 0" @click="apply">确认报名</button>
            <small>当前登录账号：{{ authStore.user?.nickname }}</small>
          </template>
          <p v-else-if="authStore.isAuthenticated">赛事管理员账号不能提交选手报名。</p>
          <RouterLink v-else class="button primary full" :to="{ path: '/login', query: { redirect: route.fullPath } }">登录后报名</RouterLink>
        </template>
        <template v-else>
          <p>赛事已开始，报名现已关闭。</p>
          <p v-if="tournament.status === 'SWISS'" class="form-hint">选手可在左侧“赛事进程”查看个人当前对阵并独立提交赛果。</p>
          <p v-if="tournament.status === 'ELIMINATION'" class="form-hint">选手可在左侧固定种子签表中查看淘汰赛对局并提交赛果。</p>
          <p v-if="tournament.status === 'ENDED'" class="form-hint">赛事结果已经永久锁定。最终四强请在左侧上传卡组截图。</p>
        </template>
      </aside>
    </div>
  </div>
  <div v-else class="page-shell empty-state"><p class="form-message">{{ error }}</p></div>
</template>
