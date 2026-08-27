export type TournamentFinishLevel =
  | 'PARTICIPATED'
  | 'TOP_8'
  | 'TOP_4'
  | 'RUNNER_UP'
  | 'CHAMPION'

export interface TournamentResultHistoryItem {
  tournament_id: string
  tournament_name: string
  ended_at: string
  participant_status: 'ACTIVE' | 'WITHDRAWN'
  finish_level: TournamentFinishLevel
  placement: number | null
  swiss_rank: number | null
  wins: number
  losses: number
  bye_count: number
  points_awarded: number
}

export interface PlayerStatistics {
  tournament_count: number
  total_points: number
  champion_count: number
  runner_up_count: number
  top_4_count: number
  top_8_count: number
  total_wins: number
  total_losses: number
  total_byes: number
  win_rate: number
  results: TournamentResultHistoryItem[]
}

export const finishLevelText: Record<TournamentFinishLevel, string> = {
  PARTICIPATED: '参赛',
  TOP_8: '八强',
  TOP_4: '四强',
  RUNNER_UP: '亚军',
  CHAMPION: '冠军',
}
