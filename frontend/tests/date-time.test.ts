import { describe, expect, it } from 'vitest'

import { combineLocalDateAndTime } from '../src/utils/dateTime'

describe('local date and time combination', () => {
  it('combines separate local values into one ISO timestamp', () => {
    const result = new Date(combineLocalDateAndTime('2026-08-25', '17:30'))

    expect(result.getFullYear()).toBe(2026)
    expect(result.getMonth()).toBe(7)
    expect(result.getDate()).toBe(25)
    expect(result.getHours()).toBe(17)
    expect(result.getMinutes()).toBe(30)
  })

  it('rejects incomplete values', () => {
    expect(() => combineLocalDateAndTime('2026-08-25', '')).toThrow('请选择有效的开赛日期和开赛时间')
  })
})
