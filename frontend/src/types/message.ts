export type MessageType =
  | 'REGISTRATION_APPROVED'
  | 'REGISTRATION_REJECTED'
  | 'REGISTRATION_CANCELED'
  | 'TOURNAMENT_NOTICE'
  | 'PLATFORM_NOTICE'
  | 'REPORT_PUBLISHED'

export interface MessageItem {
  id: string
  type: MessageType
  title: string
  body: string
  action_url: string | null
  read_at: string | null
  created_at: string
}

export interface MessageListResponse {
  items: MessageItem[]
  total: number
  unread_count: number
}

export interface UnreadCountResponse {
  unread_count: number
}

export interface MessageSendResponse {
  sent_count: number
  duplicated: boolean
}

export interface AuditLog {
  id: string
  operator_id: string
  operator_nickname: string
  tournament_id: string | null
  action_type: string
  target_type: string
  target_id: string
  before_json: Record<string, unknown> | null
  after_json: Record<string, unknown> | null
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLog[]
  total: number
}

export const messageTypeText: Record<MessageType, string> = {
  REGISTRATION_APPROVED: '报名结果',
  REGISTRATION_REJECTED: '报名结果',
  REGISTRATION_CANCELED: '报名变更',
  TOURNAMENT_NOTICE: '赛事通知',
  PLATFORM_NOTICE: '平台通知',
  REPORT_PUBLISHED: '周报发布',
}

const auditActionTypeText: Record<string, string> = {
  TOURNAMENT_CREATED_AND_PUBLISHED: '创建并发布赛事',
  TOURNAMENT_PUBLISHED: '发布赛事',
  TOURNAMENT_UPDATED: '更新赛事设置',
  TOURNAMENT_STARTED: '开始赛事',
  TOURNAMENT_ENDED: '结束赛事并锁定结果',
  REGISTRATION_APPROVE: '通过报名申请',
  REGISTRATION_REJECT: '拒绝报名申请',
  REGISTRATION_CANCEL: '取消报名资格',
  REGISTRATION_RESTORE: '恢复报名资格',
  SWISS_ROUND_GENERATED: '生成瑞士轮对阵',
  SWISS_ROUND_REGENERATED: '重新生成瑞士轮对阵',
  SWISS_PAIRING_SWAPPED: '调整瑞士轮对阵',
  SWISS_ROUND_PUBLISHED: '发布瑞士轮对阵',
  SWISS_MATCH_RESOLVED: '裁定瑞士轮赛果',
  SWISS_MATCH_FORFEIT: '裁定瑞士轮赛果',
  SWISS_PARTICIPANT_WITHDRAWN: '强制选手退赛',
  PARTICIPANT_WITHDRAWN: '强制选手退赛',
  PLAYOFF_STAGE_GENERATED: '生成淘汰赛阶段',
  PLAYOFF_STAGE_PUBLISHED: '发布淘汰赛阶段',
  PLAYOFF_STAGE_GENERATED_AND_PUBLISHED: '生成并发布淘汰赛阶段',
  PLAYOFF_MATCH_FORFEIT: '裁定淘汰赛赛果',
  PLAYOFF_MATCH_RESOLVED: '裁定淘汰赛赛果',
  DECK_SUBMISSION_APPROVE: '通过卡组审核',
  DECK_SUBMISSION_RETURN: '退回卡组重传',
  DECK_SUBMISSION_RETURNED: '退回卡组重传',
  WEEKLY_REPORT_GENERATED: '生成周报草稿',
  WEEKLY_REPORT_PUBLISHED: '发布周报',
  WEEKLY_REPORT_GENERATED_AND_PUBLISHED: '生成并发布周报',
  REPORT_GENERATED: '生成周报草稿',
  REPORT_PUBLISHED: '发布周报',
  TOURNAMENT_NOTICE_SENT: '发送赛事通知',
  PLATFORM_NOTICE_SENT: '发送平台通知',
  BANLIST_PUBLISHED: '发布禁卡表',
  BANLIST_UPDATED: '更新禁卡表',
  ANNOUNCEMENT_PUBLISHED: '发布平台公告',
  ANNOUNCEMENT_UPDATED: '更新平台公告',
}

export function auditActionText(actionType: string): string {
  return auditActionTypeText[actionType] ?? '其他系统操作'
}
