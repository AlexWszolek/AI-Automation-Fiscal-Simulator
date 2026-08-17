// The locale packs: Korean must mirror English structurally, fall back per key, resolve
// the Korea-forked lever strings, and carry the terminology charter.
import { describe, expect, it } from 'vitest'
import { packFor } from './locale'

describe('locale packs', () => {
  it('english pack is the canonical copy', () => {
    const p = packFor('en')
    expect(p.KO.sections.nps).toBe('National Pension Fund Reserves')
    expect(p.lever('us:reab').label).toBe('Reabsorption rate per year')
    expect(p.preset('korea-central').name).toBe('Korea — central')
    expect(p.group('Labor market')).toBe('Labor market')
  })

  it('korean pack translates and never drops keys', () => {
    const en = packFor('en')
    const ko = packFor('ko')
    const keysOf = (o: unknown): string[] =>
      typeof o === 'object' && o !== null
        ? Object.entries(o as object).flatMap(([k, v]) => [k, ...keysOf(v).map((s) => `${k}.${s}`)])
        : []
    for (const k of keysOf(en.KO)) {
      expect(keysOf(ko.KO)).toContain(k)
    }
    expect(ko.KO.sections.nps).toBe('국민연금기금 적립금')
    expect(ko.KO.templates.money_tn).toBe('₩{v}조')
    expect(ko.KO.templates.jobs_value).toContain('{man}')
    expect(ko.group('Labor market')).toBe('노동시장')
    expect(ko.preset('korea-agi-5y').name).toContain('코리넥')
    expect(ko.shared.share_heading).not.toBe('Share this configuration')
  })

  it('korea-forked lever strings state the korean statute, both languages', () => {
    expect(packFor('en').lever('kr:reemployment_haircut').help).toContain('statutory minimum wage')
    expect(packFor('ko').lever('kr:reemployment_haircut').help).toContain('법정 최저임금')
    expect(packFor('en').lever('kr:cons_tax_mult').help).toContain('₩79.2tn')
    expect(packFor('ko').lever('kr:corp_tax_mult').help).toContain('₩84.6조')
  })

  it('the fixed Okun sentence replaced the truncated US help in both packs', () => {
    expect(packFor('en').lever('us:demand').help).toContain('induced layoffs.')
    expect(packFor('en').lever('us:demand').help).not.toContain('multipler')
    expect(packFor('ko').lever('us:demand').help).toContain('유발 해고')
  })
})
