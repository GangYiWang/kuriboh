import { describe, expect, it } from 'vitest'

import { calculateSwissCut } from '../src/utils/swissCutCalculator'

describe('Swiss cut calculator', () => {
  it('matches the standard 16-player four-round Top 8 distribution', () => {
    const result = calculateSwissCut({ playerCount: 16, roundCount: 4, topCut: 8 })

    expect(result.guaranteedRecord).toBe('3-1')
    expect(result.maxBoundaryMisses).toBe(3)
    expect(result.groups).toEqual([{
      boundaryWins: 2,
      boundaryRecord: '2-2',
      higherRecordLabel: '3-1 及以上',
      scenarios: [{
        higherRecordCount: 5,
        boundaryPlayerCount: 6,
        boundaryQualifiers: 3,
      }],
    }])
  })

  it('collapses 27-player four-round Top 8 outcomes into four cut-line cases', () => {
    const result = calculateSwissCut({ playerCount: 27, roundCount: 4, topCut: 8 })

    expect(result.guaranteedRecord).toBe('4-0')
    expect(result.maxBoundaryMisses).toBe(2)
    expect(result.groups).toEqual([{
      boundaryWins: 3,
      boundaryRecord: '3-1',
      higherRecordLabel: '4-0 及以上',
      scenarios: [
        { higherRecordCount: 2, boundaryPlayerCount: 6, boundaryQualifiers: 6 },
        { higherRecordCount: 2, boundaryPlayerCount: 7, boundaryQualifiers: 6 },
        { higherRecordCount: 1, boundaryPlayerCount: 8, boundaryQualifiers: 7 },
        { higherRecordCount: 1, boundaryPlayerCount: 9, boundaryQualifiers: 7 },
      ],
    }])
  })

  it('rejects invalid tournament settings', () => {
    expect(() => calculateSwissCut({ playerCount: 1, roundCount: 4, topCut: 1 })).toThrow()
    expect(() => calculateSwissCut({ playerCount: 16, roundCount: 0, topCut: 8 })).toThrow()
    expect(() => calculateSwissCut({ playerCount: 16, roundCount: 4, topCut: 17 })).toThrow()
  })
})
