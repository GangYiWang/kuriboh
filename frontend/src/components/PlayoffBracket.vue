<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { apiGet, apiPost } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import MatchHistoryList from '@/components/MatchHistoryList.vue'
import PlayoffResultsTree from '@/components/PlayoffResultsTree.vue'
import type { MatchHistoryItem, MyPlayoffMatch, MySwissMatch, PlayoffOverview, SubmittedResult } from '@/types/tournament'

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
const overview = ref<PlayoffOverview | null>(null)
const myMatches = ref<MyPlayoffMatch[]>([])
const swissMatches = ref<MySwissMatch[]>([])
const busy = ref(false)
const message = ref('')
const error = ref('')
const playerMatches = computed<MatchHistoryItem[]>(() => [
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
    my_submission: item.my_submission,
    opponent_submission: item.opponent_submission,
    opponent_submitted: item.opponent_submitted,
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
    my_submission: item.my_submission,
    opponent_submission: item.opponent_submission,
    opponent_submitted: item.opponent_submitted,
  })),
]
  .sort((a, b) => b.stage_order - a.stage_order || b.round_no - a.round_no || b.table_no - a.table_no))

async function load() {
  overview.value = await apiGet<PlayoffOverview>(`/tournaments/${props.tournamentId}/playoffs`)
  if (props.view === 'matches' && props.token && props.isPlayer) {
    const [playoffItems, swissItems] = await Promise.all([
      apiGet<MyPlayoffMatch[]>(
        `/tournaments/${props.tournamentId}/playoffs/matches/me`, undefined, props.token,
      ),
      apiGet<MySwissMatch[]>(
        `/tournaments/${props.tournamentId}/matches/me`, undefined, props.token,
      ),
    ])
    myMatches.value = playoffItems
    swissMatches.value = swissItems
  }
}

async function submit(matchId: string, result: SubmittedResult) {
  busy.value = true
  message.value = ''
  error.value = ''
  try {
    await apiPost(`/playoffs/matches/${matchId}/submissions`, { result }, props.token)
    message.value = `淘汰赛赛果已提交：${result === 'WIN' ? '胜' : '负'}。`
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '淘汰赛赛果提交失败'
  } finally { busy.value = false }
}

onMounted(() => load().catch((caught) => { error.value = caught instanceof Error ? caught.message : '淘汰赛签表加载失败' }))
</script>

<template>
  <section :class="['playoff-live', { 'playoff-live-embedded': embedded }]">
    <div v-if="!embedded" class="swiss-progress-heading"><div><h2>{{ view === 'matches' ? '对阵' : '赛果' }}</h2></div><span v-if="overview" class="status-badge status-elimination">Top {{ overview.playoff_size }}</span></div>
    <FormMessage v-if="view === 'matches' && message" type="success" :message="message" />
    <FormMessage v-if="error" :message="error" />

    <template v-if="view === 'matches'">
      <MatchHistoryList v-if="isPlayer" :matches="playerMatches" :show-heading="false" interactive :busy="busy" empty-text="暂无个人对阵。" @submit="submit" />
    </template>

    <PlayoffResultsTree v-else :overview="overview" />
  </section>
</template>
