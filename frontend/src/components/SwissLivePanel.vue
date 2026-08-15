<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { apiGet, apiPost } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import MatchHistoryList from '@/components/MatchHistoryList.vue'
import type { MatchHistoryItem, MySwissMatch, SubmittedResult, SwissOverview } from '@/types/tournament'
import { matchStatusText, swissRoundStatusText } from '@/types/tournament'

const props = withDefaults(defineProps<{
  tournamentId: string
  token: string | null
  isPlayer: boolean
  view?: 'matches' | 'results'
  embedded?: boolean
}>(), {
  view: 'matches',
  embedded: false,
})
const overview = ref<SwissOverview | null>(null)
const myMatches = ref<MySwissMatch[]>([])
const busy = ref(false)
const error = ref('')
const message = ref('')
const currentMatch = computed<MySwissMatch | null>(() =>
  [...myMatches.value].reverse().find((item) => item.status !== 'COMPLETED') ?? null,
)
const currentMatchSides = computed(() => {
  const match = currentMatch.value
  if (!match) return null
  const selfIsPlayerA = match.my_participant_id === match.player_a_id
  return {
    selfId: match.my_participant_id,
    selfNickname: selfIsPlayerA ? match.player_a_nickname : match.player_b_nickname,
    opponentId: selfIsPlayerA ? match.player_b_id : match.player_a_id,
    opponentNickname: selfIsPlayerA ? match.player_b_nickname : match.player_a_nickname,
  }
})
const historyMatches = computed<MatchHistoryItem[]>(() => myMatches.value
  .filter((item) => item.status === 'COMPLETED')
  .map((item) => ({
    id: item.id,
    stage: 'SWISS' as const,
    stage_order: 1,
    round_no: item.round_no,
    round_name: `第 ${item.round_no} 轮瑞士轮`,
    table_no: item.table_no,
    player_a_id: item.player_a_id,
    player_a_nickname: item.player_a_nickname,
    player_b_id: item.player_b_id,
    player_b_nickname: item.player_b_nickname,
    winner_id: item.winner_id,
    status: item.status,
    my_participant_id: item.my_participant_id,
  }))
  .sort((a, b) => b.round_no - a.round_no || b.table_no - a.table_no))

async function load() {
  overview.value = await apiGet<SwissOverview>(`/tournaments/${props.tournamentId}/swiss`)
  if (props.view === 'matches' && props.token && props.isPlayer) {
    myMatches.value = await apiGet<MySwissMatch[]>(
      `/tournaments/${props.tournamentId}/matches/me`, undefined, props.token,
    ).catch(() => [])
  }
}

async function submit(result: SubmittedResult) {
  if (!currentMatch.value) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    await apiPost(`/matches/${currentMatch.value.id}/submissions`, { result }, props.token)
    message.value = `已提交${result === 'WIN' ? '胜' : '负'}。双方结果一致后系统会自动确认。`
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛果提交失败'
  } finally { busy.value = false }
}

onMounted(() => load().catch((caught) => { error.value = caught instanceof Error ? caught.message : '瑞士轮信息加载失败' }))
</script>

<template>
  <section :class="['swiss-live', { 'swiss-live-embedded': embedded }]">
    <div v-if="!embedded" class="swiss-progress-heading">
      <div><p class="section-kicker">{{ view === 'matches' ? 'SWISS MATCHES' : 'RESULTS' }}</p><h2>{{ view === 'matches' ? '对阵' : '赛果' }}</h2></div>
      <span v-if="overview?.current_round_status" class="status-badge status-swiss">
        第 {{ overview.current_round_no }} 轮 · {{ swissRoundStatusText[overview.current_round_status] }}
      </span>
    </div>
    <template v-if="view === 'matches'">
      <div v-if="overview" class="round-progress">
        <i :style="{ width: `${overview.total_rounds ? overview.completed_rounds / overview.total_rounds * 100 : 0}%` }" />
      </div>
      <p v-if="overview" class="form-hint">已完成 {{ overview.completed_rounds }} / {{ overview.total_rounds }} 轮；本轮未结束时继续展示第 {{ overview.ranking_round_no }} 轮后的瑞士轮排名。</p>
      <FormMessage v-if="message" type="success" :message="message" />
      <FormMessage v-if="error" :message="error" />

      <section v-if="isPlayer" class="current-match-section">
        <div class="match-section-heading"><h3>当前对阵</h3><span>本轮对局</span></div>
        <article v-if="currentMatch && currentMatchSides" class="my-match-panel">
          <div class="match-table-no">第 {{ currentMatch.round_no }} 轮瑞士轮 · {{ currentMatch.player_b_id ? `第 ${currentMatch.table_no} 桌` : '轮空' }}</div>
          <div class="match-versus">
            <strong :class="{ winner: currentMatch.winner_id === currentMatchSides.selfId }">{{ currentMatchSides.selfNickname }}</strong>
            <span>{{ currentMatchSides.opponentId ? 'VS' : 'BYE' }}</span>
            <strong v-if="currentMatchSides.opponentId" :class="{ winner: currentMatch.winner_id === currentMatchSides.opponentId }">{{ currentMatchSides.opponentNickname }}</strong>
          </div>
          <div class="match-meta">
            <span>{{ matchStatusText[currentMatch.status] }}</span>
            <span>对手{{ currentMatch.opponent_submitted ? '已提交' : '未提交' }}</span>
            <span v-if="currentMatch.my_submission">我已提交：{{ currentMatch.my_submission === 'WIN' ? '胜' : '负' }}</span>
          </div>
          <div v-if="currentMatchSides.opponentId" class="result-actions">
            <button class="button primary" type="button" aria-label="提交我获胜" :disabled="busy" @click="submit('WIN')">胜</button>
            <button class="button secondary" type="button" aria-label="提交我落败" :disabled="busy" @click="submit('LOSS')">负</button>
          </div>
          <p v-else class="form-hint">本轮轮空，系统已自动记录胜场。</p>
        </article>
        <p v-else class="empty-state compact">当前没有进行中的个人对阵。</p>
      </section>

      <MatchHistoryList v-if="isPlayer" :matches="historyMatches" />
    </template>

    <template v-else>
      <FormMessage v-if="error" :message="error" />
      <div class="ranking-heading"><h3>瑞士轮排名</h3><span>第 {{ overview?.ranking_round_no ?? 0 }} 轮快照</span></div>
      <div class="ranking-table-wrap">
        <table class="ranking-table">
          <thead><tr><th>排名</th><th>选手</th><th>胜负</th><th>OMW(%)</th><th>LRS</th></tr></thead>
          <tbody>
            <tr v-for="item in overview?.rankings" :key="item.participant_id">
              <td>{{ item.rank }}</td><td><strong>{{ item.nickname }}</strong><small v-if="item.participant_status === 'WITHDRAWN'">已退赛</small></td>
              <td>{{ item.wins }}-{{ item.losses }}</td><td>{{ (item.omw * 100).toFixed(2) }}</td><td>{{ item.loss_round_score }}</td>
            </tr>
            <tr v-if="!overview?.rankings.length"><td colspan="5">首轮全部结束后公布瑞士轮排名。</td></tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>
