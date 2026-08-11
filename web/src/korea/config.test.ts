// The Korea config layer: URL round-trips, hostile-query clamping (mirrors the server
// sanitizer so the address bar can never disagree with the API), pristine detection.
import { describe, expect, it } from 'vitest'
import {
  configFromLocation, deviations, effectiveKoreaLevers, INITIAL_KOREA, isPristine,
  KOREA_GRID, KOREA_PRESETS, presetMeta, queryStringFor,
} from './config'

describe('korea grid', () => {
  it('every preset default is inside its lever bounds', () => {
    for (const p of KOREA_PRESETS) {
      for (const [k, v] of Object.entries(p.defaults)) {
        const s = KOREA_GRID[k]
        expect(s, `${p.key}:${k}`).toBeDefined()
        expect(v, `${p.key}:${k}`).toBeGreaterThanOrEqual(s.lo)
        expect(v, `${p.key}:${k}`).toBeLessThanOrEqual(s.hi)
      }
    }
  })

  it('carries the five presets with the AGI pair last', () => {
    expect(KOREA_PRESETS.map((p) => p.key)).toEqual([
      'korea-slow', 'korea-central', 'korea-fast', 'korea-agi-20y', 'korea-agi-5y'])
  })
})

describe('url round-trip', () => {
  it('encodes only deviations and decodes them back', () => {
    const cfg = { preset: 'korea-fast', levers: { ui_weeks: 39, adoption_end: 0.6 }, overlays: [] }
    const qs = queryStringFor(cfg)
    expect(qs).toContain('preset=korea-fast')
    const back = configFromLocation(`?${qs}`)
    expect(back.preset).toBe('korea-fast')
    expect(back.levers.ui_weeks).toBe(39)
    expect(back.levers.adoption_end).toBe(0.6)
  })

  it('a pristine default config encodes to an empty query', () => {
    expect(queryStringFor(INITIAL_KOREA)).toBe('')
  })

  it('round-trips overlays and rejects unknown ones', () => {
    const cfg = { preset: 'korea-central', levers: {}, overlays: ['kr-vat', 'kr-nps-mandate'] }
    const qs = queryStringFor(cfg)
    expect(qs).toContain('ov=kr-nps-mandate%2Ckr-vat')
    const back = configFromLocation(`?${qs}`)
    expect(back.overlays).toEqual(['kr-nps-mandate', 'kr-vat'])
    expect(isPristine(back)).toBe(false)
    expect(configFromLocation('?ov=junk,kr-vat').overlays).toEqual(['kr-vat'])
  })

  it('clamps hostile query values exactly like the server sanitizer', () => {
    const cfg = configFromLocation('?preset=agi-5y&ui_weeks=400&exposure_delta=0.31&nhi_share=2&junk=9&mpc=NaN')
    expect(cfg.preset).toBe('korea-central')       // US preset key rejected
    expect(cfg.levers.ui_weeks).toBe(52)
    expect(cfg.levers.exposure_delta).toBe(0.5)    // snapped to the read grid
    expect(cfg.levers.nhi_share).toBe(KOREA_GRID.nhi_share.hi)
    expect(cfg.levers.junk).toBeUndefined()
    expect(cfg.levers.mpc).toBeUndefined()
  })
})

describe('pristine & deviations', () => {
  it('a lever set to its default is still pristine and sends nothing', () => {
    const d = presetMeta('korea-central').defaults
    const cfg = { preset: 'korea-central', levers: { ui_weeks: d.ui_weeks }, overlays: [] }
    expect(isPristine(cfg)).toBe(true)
    expect(deviations(cfg)).toEqual({})
  })

  it('effective levers = preset defaults overlaid with deviations', () => {
    const cfg = { preset: 'korea-agi-5y', levers: { ui_weeks: 10 }, overlays: [] }
    const v = effectiveKoreaLevers(cfg)
    expect(v.ui_weeks).toBe(10)
    expect(v.retained_profit_share).toBe(0.8)      // the AGI preset's override
    expect(isPristine(cfg)).toBe(false)
  })
})
