export type TournamentStatus = 'DRAFT' | 'REGISTRATION' | 'SWISS' | 'ELIMINATION' | 'ENDED'
export type RegistrationStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELED'
export type SwissRoundStatus = 'DRAFT' | 'PUBLISHED' | 'COMPLETED'
export type MatchStatus = 'WAITING' | 'CONFLICT' | 'COMPLETED'
export type SubmittedResult = 'WIN' | 'LOSS'
export type PlayoffRoundStatus = 'DRAFT' | 'PUBLISHED' | 'COMPLETED'

export interface Tournament {
  id: string
  code: string | null
  created_by_id: string
  name: string
  description: string
  planned_start_at: string | null
  max_players: number | null
  swiss_rounds: number | null
  playoff_size: number | null
  banlist_version_id: string | null
  banlist_version: string | null
  status: TournamentStatus
  published_at: string | null
  started_at: string | null
  ended_at: string | null
  approved_count: number
  pending_count: number
  created_at: string
  updated_at: string
}

export interface TournamentListResponse {
  items: Tournament[]
  total: number
}

export interface MyTournament {
  id: string
  name: string
  status: TournamentStatus
  planned_start_at: string | null
  registration_status: RegistrationStatus
  participant_status: 'ACTIVE' | 'WITHDRAWN' | null
  current_match: {
    id: string
    stage: 'SWISS' | 'ELIMINATION'
    round_no: number
    table_no: number
    opponent_nickname: string | null
    status: MatchStatus
  } | null
  ranking: { rank: number; wins: number; losses: number } | null
  report_id: string | null
}

export interface MyTournamentListResponse {
  items: MyTournament[]
  total: number
}

export interface Registration {
  id: string
  tournament_id: string
  user_id: string
  nickname: string
  status: RegistrationStatus
  reviewed_by_id: string | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface RegistrationListResponse {
  items: Registration[]
  total: number
}

export interface RegistrationBulkApproveResponse {
  approved_count: number
}

export interface Participant {
  id: string
  user_id: string
  nickname_snapshot: string
  status: 'ACTIVE' | 'WITHDRAWN'
  bye_count: number
}

export interface SwissMatch {
  id: string
  round_no: number
  table_no: number
  player_a_id: string
  player_a_nickname: string
  player_b_id: string | null
  player_b_nickname: string | null
  winner_id: string | null
  status: MatchStatus
  result_source: 'PLAYERS' | 'ADMIN' | 'BYE' | null
  result_locked: boolean
  warnings: string[]
  player_a_result: SubmittedResult | null
  player_b_result: SubmittedResult | null
}

export interface MySwissMatch extends SwissMatch {
  my_participant_id: string
  my_submission: SubmittedResult | null
  opponent_submitted: boolean
}

export interface SwissRound {
  id: string
  round_no: number
  status: SwissRoundStatus
  published_at: string | null
  completed_at: string | null
  matches: SwissMatch[]
}

export interface SwissRanking {
  participant_id: string
  nickname: string
  participant_status: 'ACTIVE' | 'WITHDRAWN'
  rank: number
  wins: number
  losses: number
  omw: number
  loss_round_score: number
}

export interface SwissOverview {
  current_round_no: number
  current_round_status: SwissRoundStatus | null
  completed_rounds: number
  total_rounds: number
  ranking_round_no: number
  rankings: SwissRanking[]
}

export interface PlayoffMatch {
  id: string
  stage_no: number
  table_no: number
  seed_a: number
  seed_b: number
  player_a_id: string
  player_a_nickname: string
  player_b_id: string
  player_b_nickname: string
  winner_id: string | null
  status: MatchStatus
  result_source: 'PLAYERS' | 'ADMIN' | null
  result_locked: boolean
  player_a_result: SubmittedResult | null
  player_b_result: SubmittedResult | null
}

export interface MyPlayoffMatch extends PlayoffMatch {
  my_participant_id: string
  my_submission: SubmittedResult | null
  opponent_submitted: boolean
}

export interface MatchHistoryItem {
  id: string
  stage: 'SWISS' | 'ELIMINATION'
  stage_order: number
  round_no: number
  round_name: string
  table_no: number
  player_a_id: string
  player_a_nickname: string
  player_b_id: string | null
  player_b_nickname: string | null
  winner_id: string | null
  status: MatchStatus
  my_participant_id: string
}

export interface PlayoffRound {
  id: string
  stage_no: number
  bracket_size: number
  name: string
  status: PlayoffRoundStatus
  published_at: string | null
  completed_at: string | null
  matches: PlayoffMatch[]
}

export interface PlayoffOverview {
  playoff_size: number
  rounds: PlayoffRound[]
  champion_id: string | null
  champion_nickname: string | null
  awaiting_tournament_end: boolean
}

export const swissRoundStatusText: Record<SwissRoundStatus, string> = {
  DRAFT: '预览未发布',
  PUBLISHED: '进行中',
  COMPLETED: '已完成',
}

export const matchStatusText: Record<MatchStatus, string> = {
  WAITING: '等待提交',
  CONFLICT: '赛果冲突',
  COMPLETED: '已完成',
}

export const tournamentStatusText: Record<TournamentStatus, string> = {
  DRAFT: '草稿',
  REGISTRATION: '报名中',
  SWISS: '瑞士轮',
  ELIMINATION: '淘汰赛',
  ENDED: '已结束',
}

export const registrationStatusText: Record<RegistrationStatus, string> = {
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已拒绝',
  CANCELED: '已取消',
}
