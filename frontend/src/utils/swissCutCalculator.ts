export interface SwissCutInput {
  playerCount: number
  roundCount: number
  topCut: number
}

export interface SwissCutScenario {
  higherRecordCount: number
  boundaryPlayerCount: number
  boundaryQualifiers: number
}

export interface SwissCutGroup {
  boundaryWins: number
  boundaryRecord: string
  higherRecordLabel: string
  scenarios: SwissCutScenario[]
}

export interface SwissCutResult {
  guaranteedRecord: string
  maxBoundaryMisses: number
  groups: SwissCutGroup[]
}

interface CutSummary extends SwissCutScenario {
  boundaryWins: number
}

const MAX_PLAYER_COUNT = 1024
const MAX_ROUND_COUNT = 12
const MAX_STATE_COUNT = 50_000

function stateKey(state: number[]): string {
  return state.join(',')
}

function uniqueStates(states: number[][]): number[][] {
  return [...new Map(states.map((state) => [stateKey(state), state])).values()]
}

function advanceRound(state: number[]): number[][] {
  const counts = [...state]
  const nextBase = Array.from({ length: state.length + 1 }, () => 0)
  const totalPlayers = counts.reduce((total, count) => total + count, 0)

  if (totalPlayers % 2 === 1) {
    const byeScore = counts.findIndex((count) => count > 0)
    if (byeScore < 0) return []
    counts[byeScore] -= 1
    nextBase[byeScore + 1] += 1
  }

  const crossGroupMatches: Array<[number, number]> = []
  for (let score = counts.length - 1; score >= 0; score -= 1) {
    if (counts[score] % 2 === 1) {
      if (score === 0 || counts[score - 1] === 0) return []
      counts[score] -= 1
      counts[score - 1] -= 1
      crossGroupMatches.push([score, score - 1])
    }

    const sameGroupMatches = counts[score] / 2
    nextBase[score] += sameGroupMatches
    nextBase[score + 1] += sameGroupMatches
  }

  let states = [nextBase]
  for (const [higherScore, lowerScore] of crossGroupMatches) {
    states = states.flatMap((current) => {
      const higherPlayerWins = [...current]
      higherPlayerWins[higherScore + 1] += 1
      higherPlayerWins[lowerScore] += 1

      const lowerPlayerWins = [...current]
      lowerPlayerWins[higherScore] += 1
      lowerPlayerWins[lowerScore + 1] += 1
      return [higherPlayerWins, lowerPlayerWins]
    })
  }
  return uniqueStates(states)
}

function summarizeCut(state: number[], topCut: number): CutSummary {
  let higherRecordCount = 0
  for (let wins = state.length - 1; wins >= 0; wins -= 1) {
    const playerCount = state[wins]
    if (higherRecordCount + playerCount >= topCut) {
      return {
        boundaryWins: wins,
        higherRecordCount,
        boundaryPlayerCount: playerCount,
        boundaryQualifiers: Math.max(0, topCut - higherRecordCount),
      }
    }
    higherRecordCount += playerCount
  }
  throw new Error('无法确定晋级线')
}

function formatRecord(wins: number, rounds: number): string {
  return `${wins}-${rounds - wins}`
}

function validateInput(input: SwissCutInput): void {
  if (!Number.isInteger(input.playerCount) || input.playerCount < 2 || input.playerCount > MAX_PLAYER_COUNT) {
    throw new RangeError(`玩家人数必须是 2 到 ${MAX_PLAYER_COUNT} 之间的整数`)
  }
  if (!Number.isInteger(input.roundCount) || input.roundCount < 1 || input.roundCount > MAX_ROUND_COUNT) {
    throw new RangeError(`回合数必须是 1 到 ${MAX_ROUND_COUNT} 之间的整数`)
  }
  if (!Number.isInteger(input.topCut) || input.topCut < 1 || input.topCut > input.playerCount) {
    throw new RangeError('晋级人数必须是不超过玩家人数的正整数')
  }
}

export function calculateSwissCut(input: SwissCutInput): SwissCutResult {
  validateInput(input)
  let states: number[][] = [[input.playerCount]]
  for (let round = 0; round < input.roundCount; round += 1) {
    states = uniqueStates(states.flatMap(advanceRound))
    if (!states.length) throw new Error('当前人数与回合数组合无法生成完整的相邻胜场组配对')
    if (states.length > MAX_STATE_COUNT) throw new Error('可能情况过多，请减少回合数后重试')
  }

  const summaries = [...new Map(
    states.map((state) => {
      const summary = summarizeCut(state, input.topCut)
      const key = [
        summary.boundaryWins,
        summary.higherRecordCount,
        summary.boundaryPlayerCount,
        summary.boundaryQualifiers,
      ].join(':')
      return [key, summary]
    }),
  ).values()]

  const guaranteedWins = Math.max(...summaries.map((summary) => (
    summary.boundaryQualifiers < summary.boundaryPlayerCount
      ? summary.boundaryWins + 1
      : summary.boundaryWins
  )))
  const maxBoundaryMisses = Math.max(...summaries.map(
    (summary) => summary.boundaryPlayerCount - summary.boundaryQualifiers,
  ))
  const boundaryWins = [...new Set(summaries.map((summary) => summary.boundaryWins))]
    .sort((left, right) => right - left)
  const groups = boundaryWins.map((wins) => ({
    boundaryWins: wins,
    boundaryRecord: formatRecord(wins, input.roundCount),
    higherRecordLabel: `${formatRecord(wins + 1, input.roundCount)} 及以上`,
    scenarios: summaries
      .filter((summary) => summary.boundaryWins === wins)
      .map((summary) => ({
        higherRecordCount: summary.higherRecordCount,
        boundaryPlayerCount: summary.boundaryPlayerCount,
        boundaryQualifiers: summary.boundaryQualifiers,
      }))
      .sort((left, right) => (
        right.higherRecordCount - left.higherRecordCount
        || left.boundaryPlayerCount - right.boundaryPlayerCount
        || left.boundaryQualifiers - right.boundaryQualifiers
      )),
  }))

  return {
    guaranteedRecord: formatRecord(guaranteedWins, input.roundCount),
    maxBoundaryMisses,
    groups,
  }
}
