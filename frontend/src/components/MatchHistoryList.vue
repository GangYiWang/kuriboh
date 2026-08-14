<script setup lang="ts">
import type { MatchHistoryItem } from '@/types/tournament'
import { matchStatusText } from '@/types/tournament'

defineProps<{ matches: MatchHistoryItem[] }>()

function resultText(match: MatchHistoryItem, participantId: string | null) {
  if (!participantId || match.status !== 'COMPLETED') return ''
  return match.winner_id === participantId ? '胜' : '负'
}
</script>

<template>
  <section class="match-history-section">
    <div class="ranking-heading"><h2>历史对阵</h2><span>最新对局优先</span></div>
    <div v-if="matches.length" class="match-history-list">
      <article v-for="match in matches" :key="`${match.stage}-${match.id}`" class="history-match-card">
        <header>
          <strong>{{ match.round_name }}</strong>
          <span>{{ match.player_b_id ? `第 ${match.table_no} 桌` : '轮空' }}</span>
          <i>{{ matchStatusText[match.status] }}</i>
        </header>
        <div class="history-player" :class="{ winner: match.winner_id === match.player_a_id }">
          <span>{{ match.player_a_id === match.my_participant_id ? '我' : '对手' }}</span>
          <strong>{{ match.player_a_nickname }}</strong>
          <i>{{ resultText(match, match.player_a_id) }}</i>
        </div>
        <div v-if="match.player_b_id" class="history-player" :class="{ winner: match.winner_id === match.player_b_id }">
          <span>{{ match.player_b_id === match.my_participant_id ? '我' : '对手' }}</span>
          <strong>{{ match.player_b_nickname }}</strong>
          <i>{{ resultText(match, match.player_b_id) }}</i>
        </div>
        <div v-else class="history-player history-bye"><span>对手</span><strong>轮空（BYE）</strong><i>—</i></div>
      </article>
    </div>
    <p v-else class="empty-state compact">尚无已完成的历史对阵。</p>
  </section>
</template>
