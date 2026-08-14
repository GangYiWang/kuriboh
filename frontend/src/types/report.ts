export type DeckSubmissionStatus = 'NOT_UPLOADED' | 'PENDING_REVIEW' | 'REUPLOAD_REQUIRED' | 'APPROVED'
export type WeeklyReportStatus = 'DRAFT' | 'PUBLISHED'

export interface DeckSubmission {
  id: string
  tournament_id: string
  participant_id: string
  user_id: string
  nickname: string
  placement: number
  image_url: string | null
  status: DeckSubmissionStatus
  review_note: string | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface DeckSubmissionList {
  items: DeckSubmission[]
  approved_count: number
  required_count: number
}

export interface ReportTournamentSnapshot {
  name: string
  competition_time: string
  ended_at: string | null
  participant_count: number
  swiss_rounds: number
  playoff_size: number
  format: string
}

export interface ReportPodiumItem {
  placement: number
  nickname: string
  image_url: string
}

export interface ReportRankingItem {
  rank: number
  nickname: string
  wins: number
  losses: number
  omw: number
  loss_round_score: number
}

export interface ReportPlayoffMatch {
  seed_a: number
  player_a: string
  seed_b: number
  player_b: string
  winner: string
}

export interface ReportSnapshot {
  template_version: number
  tournament: ReportTournamentSnapshot
  podium: ReportPodiumItem[]
  swiss_rankings: ReportRankingItem[]
  playoff_rounds: Array<{ name: string; stage_no: number; matches: ReportPlayoffMatch[] }>
}

export interface WeeklyReport {
  id: string
  tournament_id: string
  tournament_name: string
  status: WeeklyReportStatus
  snapshot_content: ReportSnapshot
  published_at: string | null
  created_at: string
}

export interface WeeklyReportList {
  items: WeeklyReport[]
  total: number
}

export const deckStatusText: Record<DeckSubmissionStatus, string> = {
  NOT_UPLOADED: '尚未上传',
  PENDING_REVIEW: '待管理员审核',
  REUPLOAD_REQUIRED: '需重新上传',
  APPROVED: '审核通过',
}
