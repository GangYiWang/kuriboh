<script setup lang="ts">
import type { MatchHistoryItem, SubmittedResult } from '@/types/tournament'
import { matchStatusText } from '@/types/tournament'

withDefaults(defineProps<{
  matches: MatchHistoryItem[]
  title?: string
  subtitle?: string
  showHeading?: boolean
  interactive?: boolean
  busy?: boolean
  emptyText?: string
}>(), {
  title: '历史对阵',
  subtitle: '最新对局优先',
  showHeading: true,
  interactive: false,
  busy: false,
  emptyText: '尚无已完成的历史对阵。',
})

const emit = defineEmits<{
  submit: [matchId: string, result: SubmittedResult]
}>()

function resultText(match: MatchHistoryItem, participantId: string | null) {
  if (!participantId || match.status !== 'COMPLETED') return ''
  return match.winner_id === participantId ? '胜' : '负'
}

function selfIsPlayerA(match: MatchHistoryItem) {
  return match.my_participant_id === match.player_a_id
}

function selfParticipantId(match: MatchHistoryItem) {
  return selfIsPlayerA(match) ? match.player_a_id : match.player_b_id
}

function opponentParticipantId(match: MatchHistoryItem) {
  return selfIsPlayerA(match) ? match.player_b_id : match.player_a_id
}

function selfNickname(match: MatchHistoryItem) {
  return selfIsPlayerA(match) ? match.player_a_nickname : match.player_b_nickname
}

function opponentNickname(match: MatchHistoryItem) {
  return selfIsPlayerA(match) ? match.player_b_nickname : match.player_a_nickname
}

function submissionResultText(result: SubmittedResult) {
  return result === 'WIN' ? '胜' : '负'
}
</script>

<template>
  <section :class="['match-history-section', { 'match-history-section-headingless': !showHeading }]">
    <div v-if="showHeading" class="match-section-heading"><h3>{{ title }}</h3><span>{{ subtitle }}</span></div>
    <div v-if="matches.length" class="match-history-list">
      <article v-for="match in matches" :key="`${match.stage}-${match.id}`" :class="['history-match-card', { 'history-match-card-active': match.status !== 'COMPLETED' }]">
        <header>
          <strong>{{ match.round_name }}</strong>
          <span>{{ match.player_b_id ? `第 ${match.table_no} 桌` : '轮空' }}</span>
          <i :class="`match-status-${match.status.toLowerCase()}`">{{ matchStatusText[match.status] }}</i>
        </header>
        <div class="history-match-versus">
          <div class="history-match-side history-match-self" :class="{ winner: match.winner_id === selfParticipantId(match) }">
            <strong>{{ selfNickname(match) }}</strong>
            <i v-if="match.status === 'COMPLETED'">{{ resultText(match, selfParticipantId(match)) }}</i>
            <i
              v-else-if="interactive && match.my_submission"
              :class="{ 'submission-win': match.my_submission === 'WIN' }"
              aria-label="我的已提交赛果"
            >{{ submissionResultText(match.my_submission) }}</i>
          </div>
          <span class="history-versus-mark">VS</span>
          <div class="history-match-side history-match-opponent" :class="{ winner: match.winner_id === opponentParticipantId(match), 'history-bye': !opponentParticipantId(match) }">
            <i v-if="match.status === 'COMPLETED'">{{ resultText(match, opponentParticipantId(match)) || '—' }}</i>
            <i
              v-else-if="interactive && match.opponent_submitted && match.opponent_submission"
              :class="{ 'submission-win': match.opponent_submission === 'WIN' }"
              aria-label="对手已提交赛果"
            >{{ submissionResultText(match.opponent_submission) }}</i>
            <strong>{{ opponentNickname(match) || '轮空（BYE）' }}</strong>
          </div>
        </div>
        <template v-if="interactive && match.status !== 'COMPLETED' && match.player_b_id">
          <div class="history-match-actions">
            <button class="history-result-button submission-win" type="button" aria-label="提交我获胜" :disabled="busy" @click="emit('submit', match.id, 'WIN')">胜</button>
            <button class="history-result-button" type="button" aria-label="提交我落败" :disabled="busy" @click="emit('submit', match.id, 'LOSS')">负</button>
          </div>
        </template>
      </article>
    </div>
    <p v-else class="empty-state compact">{{ emptyText }}</p>
  </section>
</template>
