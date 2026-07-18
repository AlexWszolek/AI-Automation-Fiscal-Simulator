// The codec goldens: every vector was produced by CALLING the Python codec — the TS port must
// reproduce all of them exactly. This is the front end's most important test.
import { describe, expect, it } from 'vitest'
import vectors from '../gen/codec_vectors.json'
import { encodeQuery, parseQuery } from './codec'
import type { LeverValue } from './types'

interface ParseVector {
  qp: Record<string, string>
  expect: { preset: string | null; overlays: string[]; levers: Record<string, LeverValue> }
}
interface EncodeVector {
  preset: string | null
  overlays: string[]
  current: Record<string, LeverValue>
  pristine: Record<string, LeverValue>
  expect: Record<string, string>
}

describe('parse golden vectors', () => {
  for (const [i, v] of (vectors.parse as unknown as ParseVector[]).entries()) {
    it(`#${i} ${JSON.stringify(v.qp).slice(0, 60)}`, () => {
      const got = parseQuery(v.qp)
      expect(got.preset).toBe(v.expect.preset)
      expect(got.overlays).toEqual(v.expect.overlays)
      expect(got.levers).toEqual(v.expect.levers)
    })
  }
})

describe('encode golden vectors', () => {
  for (const [i, v] of (vectors.encode as unknown as EncodeVector[]).entries()) {
    it(`#${i} preset=${v.preset}`, () => {
      expect(encodeQuery(v.preset, v.overlays, v.current, v.pristine)).toEqual(v.expect)
    })
  }
})
