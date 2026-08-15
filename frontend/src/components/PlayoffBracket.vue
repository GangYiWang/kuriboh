<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { apiGet, apiPost } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import MatchHistoryList from '@/components/MatchHistoryList.vue'
import type { MatchHistoryItem, MyPlayoffMatch, MySwissMatch, PlayoffOverview, SubmittedResult } from '@/types/tournament'
import { matchStatusText, swissRoundStatusText } from '@/types/tournament'

const props = defineProps<{ tournamentId: string; token: string | null; isPlayer: boolean }>()
const overview = ref<PlayoffOverview | null>(null)
const myMatches = ref<MyPlayoffMatch[]>([])
const swissMatches = ref<MySwissMatch[]>([])
const busy = ref(false)
const message = ref('')
const error = ref('')
const currentMatch = computed(() => [...myMatches.value].reverse().find((item) => item.status !== 'COMPLETED') ?? myMatches.value[myMatches.value.length - 1] ?? null)
const historyMatches = computed<MatchHistoryItem[]>(() => [
  ...myMatches.value.map((item) => ({
    id: item.id,
    stage: 'ELIMINATION' as const,
    stage_order: 2,
    round_no: item.stage_no,
    round_name: `淘汰赛 · ${overview.value?.rounds.find((round) => round.stage_no === item.stage_no)?.name ?? `第 ${item.stage_no} 阶段`}`,
    table_no: item.table_no,
    player_a_id: item.player_a_id,
    player_a_nickname: item.player_a_nickname,
    player_b_id: item.player_b_id,
    player_b_nickname: item.player_b_nickname,
    winner_id: item.winner_id,
    status: item.status,
    my_participant_id: item.my_participant_id,
  })),
  ...swissMatches.value.map((item) => ({
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
  })),
]
  .filter((item) => item.status === 'COMPLETED')
  .sort((a, b) => b.stage_order - a.stage_order || b.round_no - a.round_no || b.table_no - a.table_no))

async function load() {
  overview.value = await apiGet<PlayoffOverview>(`/tournaments/${props.tournamentId}/playoffs`)
  if (props.token && props.isPlayer) {
    const [playoffItems, swissItems] = await Promise.all([
      apiGet<MyPlayoffMatch[]>(
        `/tournaments/${props.tournamentId}/playoffs/matches/me`, undefined, props.token,
      ).catch(() => []),
      apiGet<MySwissMatch[]>(
        `/tournaments/${props.tournamentId}/matches/me`, undefined, props.token,
      ).catch(() => []),
    ])
    myMatches.value = playoffItems
    swissMatches.value = swissItems
  }
}

async function submit(result: SubmittedResult) {
  if (!currentMatch.value) return
  busy.value = true
  message.value = ''
  error.value = ''
  try {
    await apiPost(`/playoffs/matches/${currentMatch.value.id}/submissions`, { result }, props.token)
    message.value = `淘汰赛赛果已提交：${result === 'WIN' ? '胜' : '负'}。`
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '淘汰赛赛果提交失败'
  } finally { busy.value = false }
}

onMounted(() => load().catch((caught) => { error.value = caught instanceof Error ? caught.message : '淘汰赛签表加载失败' }))
</script>

<template>
  <section class="playoff-live">
    <div class="swiss-progress-heading"><div><p class="section-kicker">PLAYOFF BRACKET</p><h2>淘汰赛签表</h2></div><span v-if="overview" class="status-badge status-elimination">Top {{ overview.playoff_size }}</span></div>
    <FormMessage v-if="message" type="success" :message="message" />
    <FormMessage v-if="error" :message="error" />
    <div v-if="overview?.champion_nickname" class="champion-strip"><span>CHAMPION</span><strong>{{ overview.champion_nickname }}</strong><small>{{ overview.awaiting_tournament_end ? '决赛已完成，等待管理员结束赛事。' : '赛事已结束，全部结果已永久锁定。' }}</small></div>

    <article v-if="currentMatch && currentMatch.status !== 'COMPLETED'" class="my-match-panel playoff-current-match">
      <div class="match-table-no">淘汰赛 · {{ overview?.rounds.find((item) => item.stage_no === currentMatch.stage_no)?.name }} · 第 {{ currentMatch.table_no }} 桌</div>
      <div class="match-versus"><strong>#{{ currentMatch.seed_a }} {{ currentMatch.player_a_nickname }}</strong><span>VS</span><strong>#{{ currentMatch.seed_b }} {{ currentMatch.player_b_nickname }}</strong></div>
      <div class="match-meta"><span>{{ matchStatusText[currentMatch.status] }}</span><span>对手{{ currentMatch.opponent_submitted ? '已提交' : '未提交' }}</span><span v-if="currentMatch.my_submission">我已提交：{{ currentMatch.my_submission === 'WIN' ? '胜' : '负' }}</span></div>
      <div class="result-actions"><button class="button primary" type="button" aria-label="提交我获胜" :disabled="busy" @click="submit('WIN')">胜</button><button class="button secondary" type="button" aria-label="提交我落败" :disabled="busy" @click="submit('LOSS')">负</button></div>
    </article>

    <MatchHistoryList v-if="isPlayer" :matches="historyMatches" />

    <div class="playoff-bracket" :style="{ '--round-count': overview?.rounds.length || 1 }">
      <section v-for="round in overview?.rounds" :key="round.id" class="bracket-round">
        <header><strong>{{ round.name }}</strong><span>{{ swissRoundStatusText[round.status] }}</span></header>
        <div class="bracket-match-list">
          <article v-for="match in round.matches" :key="match.id" class="bracket-match">
            <div :class="{ winner: match.winner_id === match.player_a_id }"><span>#{{ match.seed_a }}</span><strong>{{ match.player_a_nickname }}</strong><i>{{ match.winner_id === match.player_a_id ? 'W' : '' }}</i></div>
            <div :class="{ winner: match.winner_id === match.player_b_id }"><span>#{{ match.seed_b }}</span><strong>{{ match.player_b_nickname }}</strong><i>{{ match.winner_id === match.player_b_id ? 'W' : '' }}</i></div>
          </article>
        </div>
      </section>
    </div>
    <p v-if="!overview?.rounds.length" class="empty-state compact">管理员发布首个淘汰阶段后显示固定种子签表。</p>
  </section>
</template>
