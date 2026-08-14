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
