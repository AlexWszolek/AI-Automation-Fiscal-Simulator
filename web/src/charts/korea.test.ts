// The Korea spec builders: shape, series identity, and the validated color pair. These are
// structural tests — the numbers themselves are pinned python-side (test_korea_bundle.py).
import { describe, expect, it } from 'vitest'
import { compositionBars, contrastBars, fundBand, type KoreaFund } from './korea'

const FUND: KoreaFund = {
  years: [2026, 2027, 2028],
  published: [10, 5, -1],
  eroded_central: [9.5, 4.2, -2.1],
  eroded_lo: [9.0, 3.5, -3.0],
  eroded_hi: [9.8, 4.8, -1.5],
  published_depletion: 2028,
}
const LABELS = { published: 'Published projection', eroded: 'With automation (central)', band: 'Automation band' }

describe('fundBand', () => {
  const spec = fundBand(FUND, '₩ trillions', LABELS) as Record<string, unknown>
  const layers = spec.layer as Record<string, unknown>[]

  it('has band, zero-rule, lines, and crosshair layers', () => {
    expect(layers).toHaveLength(4)
    const band = layers[0] as { mark: { type: string; opacity: number } }
    expect(band.mark.type).toBe('area')
    expect(band.mark.opacity).toBeLessThan(0.3)      // envelope, not a filled series
  })

  it('draws exactly the two named series with the validated pair', () => {
    const lines = layers[2] as {
      data: { values: { series: string }[] }
      encoding: { color: { scale: { domain: string[]; range: string[] } } }
    }
    expect(lines.encoding.color.scale.domain).toEqual([LABELS.published, LABELS.eroded])
    expect(lines.encoding.color.scale.range).toEqual(['#3b6ea5', '#8c2f28'])
    const series = new Set(lines.data.values.map((v) => v.series))
    expect(series).toEqual(new Set([LABELS.published, LABELS.eroded]))
    expect(lines.data.values).toHaveLength(6)        // 3 years × 2 series
  })

  it('band rows carry lo ≤ central ≤ hi for every year', () => {
    const rows = (layers[0] as { data: { values: Record<string, number>[] } }).data.values
    for (const r of rows) {
      expect(r.lo).toBeLessThanOrEqual(r.central)
      expect(r.central).toBeLessThanOrEqual(r.hi)
    }
  })
})

describe('compositionBars', () => {
  it('is a single-hue bar with direct labels (identity lives on the axis)', () => {
    const spec = compositionBars({ a: 0.08, b: 0.086 }, (k) => k.toUpperCase()) as {
      layer: { mark: { type: string; color?: string } }[]
      data?: unknown
    }
    expect(spec.layer[0].mark.type).toBe('bar')
    expect(spec.layer[0].mark.color).toBe('#8c2f28')   // the loss hue: base ERODED
    expect(spec.layer[1].mark.type).toBe('text')
    const rows = (spec as unknown as { data: { values: { label: string }[] } }).data.values
    expect(rows.map((r) => r.label)).toEqual(['A', 'B'])
  })
})

describe('contrastBars', () => {
  it('grouped bars with the two scenarios in the validated pair', () => {
    const spec = contrastBars({ a: 0.3 }, { a: 0.05 }, { a: 'White', b: 'Elementary' },
      (k) => k) as { encoding: { color: { scale: { domain: string[]; range: string[] } } },
                     data: { values: unknown[] } }
    expect(spec.encoding.color.scale.domain).toEqual(['White', 'Elementary'])
    expect(spec.encoding.color.scale.range).toEqual(['#3b6ea5', '#8c2f28'])
    expect(spec.data.values).toHaveLength(2)
  })
})
