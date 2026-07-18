import { describe, expect, it } from 'vitest'
import { MINUS, dollarsB, dollarsHero, pct, signed, thousands } from './format'

describe('format', () => {
  it('uses the true minus, never the hyphen', () => {
    expect(signed(-664)).toBe(`${MINUS}664`)
    expect(pct(-29)).toBe(`${MINUS}29%`)
    expect(dollarsB(-664)).toBe(`${MINUS}$664B`)
    expect(signed(-664)).not.toContain('-')
  })
  it('abbreviates hero dollars at a trillion', () => {
    expect(dollarsHero(2674)).toBe('$2.67T')
    expect(dollarsHero(664)).toBe('$664B')
    expect(dollarsHero(-14321)).toBe(`${MINUS}$14.32T`)
  })
  it('keeps tables exact', () => {
    expect(dollarsB(2674)).toBe('$2,674B')
    expect(thousands(1234.56, 1)).toBe('1,234.6')
  })
})
