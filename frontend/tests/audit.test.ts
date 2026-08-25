import { describe, expect, it } from 'vitest'

import { auditActionText } from '../src/types/message'

describe('audit action labels', () => {
  it('translates current and legacy action codes into Chinese', () => {
    expect(auditActionText('WEEKLY_REPORT_GENERATED_AND_PUBLISHED')).toBe('生成并发布周报')
    expect(auditActionText('WEEKLY_REPORT_GENERATED')).toBe('生成周报草稿')
    expect(auditActionText('DECK_SUBMISSION_APPROVE')).toBe('通过卡组审核')
    expect(auditActionText('TOURNAMENT_ENDED')).toBe('结束赛事并锁定结果')
  })

  it('does not expose unknown English codes as page titles', () => {
    expect(auditActionText('FUTURE_UNKNOWN_ACTION')).toBe('其他系统操作')
  })
})
