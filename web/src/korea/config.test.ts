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

  it('carries the ten presets, diffusion trio first, AGI pair last', () => {
    expect(KOREA_PRESETS.map((p) => p.key)).toEqual([
      'korea-slow', 'korea-central', 'korea-fast',
      'korea-acemoglu', 'korea-brynjolfsson', 'korea-karger', 'korea-metaculus',
      'korea-ai-2027', 'korea-agi-20y', 'korea-agi-5y'])
  })
})

describe('url round-trip', () => {
  it('encodes only deviations and decodes them back', () => {
    const cfg = { preset: 'korea-fast', levers: { ui_weeks: 39, adoption_end: 0.6 } }
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

  it('legacy overlay links translate to the policy levers', () => {
    const back = configFromLocation('?ov=kr-nps-mandate,kr-vat')
    expect(back.levers.vat_pp).toBe(1)
    expect(back.levers.nps_mandate_share).toBe(0.2)
    expect(isPristine(back)).toBe(false)
    expect(configFromLocation('?ov=junk').levers).toEqual({})
  })

  it('the policy levers ride the normal lever codec', () => {
    const cfg = { preset: 'korea-central', levers: { corp_to_funds: 0.5, vat_pp: 2 } }
    const back = configFromLocation(`?${queryStringFor(cfg)}`)
    expect(back.levers.corp_to_funds).toBe(0.5)
    expect(back.levers.vat_pp).toBe(2)
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
    const cfg = { preset: 'korea-central', levers: { ui_weeks: d.ui_weeks } }
    expect(isPristine(cfg)).toBe(true)
    expect(deviations(cfg)).toEqual({})
  })

  it('effective levers = preset defaults overlaid with deviations', () => {
    const cfg = { preset: 'korea-agi-5y', levers: { ui_weeks: 10 } }
    const v = effectiveKoreaLevers(cfg)
    expect(v.ui_weeks).toBe(10)
    expect(v.retained_profit_share).toBe(0.8)      // the AGI preset's override
    expect(isPristine(cfg)).toBe(false)
  })
})
