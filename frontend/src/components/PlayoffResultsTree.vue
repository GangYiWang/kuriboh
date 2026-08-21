<script setup lang="ts">
import { computed } from 'vue'

import type { PlayoffMatch, PlayoffOverview, PlayoffRound } from '@/types/tournament'

type BracketPlayer = {
  id: string
  nickname: string
  seed: number
}

type BracketTreeSlot = {
  key: string
  match: PlayoffMatch | null
  playerA: BracketPlayer | null
  playerB: BracketPlayer | null
  slotIndex: number
  slotSpan: number
}

type BracketTreeRound = {
  key: string
  name: string
  bracketSize: number
  round: PlayoffRound | null
  slots: BracketTreeSlot[]
}

const props = defineProps<{
  overview: PlayoffOverview | null
}>()

const treeRounds = computed<BracketTreeRound[]>(() => {
  const overview = props.overview
  if (!overview?.rounds.length || overview.playoff_size < 2) return []

  const actualRounds = new Map(overview.rounds.map((round) => [round.bracket_size, round]))
  const roundNames: Record<number, string> = { 2: '决赛', 4: '半决赛', 8: '八强', 16: '十六强', 32: '三十二强', 64: '六十四强' }
  const result: BracketTreeRound[] = []
  let previousSlots: BracketTreeSlot[] = []

  for (let bracketSize = overview.playoff_size; bracketSize >= 2; bracketSize /= 2) {
    const round = actualRounds.get(bracketSize) ?? null
    const slotSpan = overview.playoff_size / bracketSize
    const matchCount = bracketSize / 2
    const sortedMatches = round ? [...round.matches].sort((a, b) => a.table_no - b.table_no) : []
    const slots = Array.from({ length: matchCount }, (_, slotIndex): BracketTreeSlot => {
      const match = sortedMatches[slotIndex] ?? null
      const sourceA = previousSlots[slotIndex * 2]
      const sourceB = previousSlots[slotIndex * 2 + 1]
      const sourceWinner = (source: BracketTreeSlot | undefined): BracketPlayer | null => {
        if (!source?.match?.winner_id) return null
        return source.match.winner_id === source.match.player_a_id ? source.playerA : source.playerB
      }
      return {
        key: match?.id ?? `placeholder-${bracketSize}-${slotIndex}`,
        match,
        playerA: match
          ? { id: match.player_a_id, nickname: match.player_a_nickname, seed: match.seed_a }
          : sourceWinner(sourceA),
        playerB: match
          ? { id: match.player_b_id, nickname: match.player_b_nickname, seed: match.seed_b }
          : sourceWinner(sourceB),
        slotIndex,
        slotSpan,
      }
    })
    result.push({
      key: round?.id ?? `placeholder-round-${bracketSize}`,
      name: round?.name ?? (roundNames[bracketSize] ?? `Top ${bracketSize}`),
      bracketSize,
      round,
      slots,
    })
    previousSlots = slots
  }
  return result
})
</script>

<template>
  <section v-if="treeRounds.length" class="playoff-results-bracket">
    <div class="ranking-heading"><h3>淘汰赛晋级图</h3></div>
    <div
      class="playoff-bracket-tree"
      :style="{ '--round-count': treeRounds.length, '--base-match-count': (overview?.playoff_size ?? 2) / 2 }"
      aria-label="淘汰赛晋级结果树"
    >
      <section v-for="(treeRound, roundIndex) in treeRounds" :key="treeRound.key" class="bracket-tree-round">
        <header><strong>{{ treeRound.name }}</strong></header>
        <div class="bracket-tree-slot-list">
          <article
            v-for="slot in treeRound.slots"
            :key="slot.key"
            class="bracket-tree-slot"
            :style="{ gridRow: `${slot.slotIndex * slot.slotSpan + 1} / span ${slot.slotSpan}`, '--slot-span': slot.slotSpan }"
          >
            <i v-if="roundIndex < treeRounds.length - 1 && slot.slotIndex % 2 === 0" class="bracket-merge-line" aria-hidden="true" />
            <div :class="['bracket-match', { 'bracket-match-placeholder': !slot.match }]">
              <div :class="{ winner: Boolean(slot.match?.winner_id && slot.match.winner_id === slot.playerA?.id), advanced: !slot.match && slot.playerA }">
                <span>{{ slot.playerA ? `#${slot.playerA.seed}` : '—' }}</span><strong>{{ slot.playerA?.nickname || '待定' }}</strong><i>{{ slot.match?.winner_id && slot.match.winner_id === slot.playerA?.id ? '胜' : '' }}</i>
              </div>
              <div :class="{ winner: Boolean(slot.match?.winner_id && slot.match.winner_id === slot.playerB?.id), advanced: !slot.match && slot.playerB }">
                <span>{{ slot.playerB ? `#${slot.playerB.seed}` : '—' }}</span><strong>{{ slot.playerB?.nickname || '待定' }}</strong><i>{{ slot.match?.winner_id && slot.match.winner_id === slot.playerB?.id ? '胜' : '' }}</i>
              </div>
            </div>
          </article>
        </div>
      </section>
    </div>
  </section>
  <p v-else class="empty-state">生成首个淘汰阶段后显示完整 Bracket 晋级图。</p>
</template>
