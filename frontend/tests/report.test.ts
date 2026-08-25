import { describe, expect, it } from 'vitest'

import { deckPlacementText } from '../src/types/report'

describe('deck placement labels', () => {
  it('does not distinguish the two semifinalists', () => {
    expect(deckPlacementText(1)).toBe('冠军')
    expect(deckPlacementText(2)).toBe('亚军')
    expect(deckPlacementText(3)).toBe('四强')
    expect(deckPlacementText(4)).toBe('四强')
  })
})
