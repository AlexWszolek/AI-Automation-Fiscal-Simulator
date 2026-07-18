// The shareable-URL codec — a TS port of fiscal_model/app_params.py's parse_query_config /
// encode_query_config, pinned to the Python behavior by ~200 generated golden vectors
// (gen/codec_vectors.json, tested in codec.test.ts). Old shared links MUST keep resolving
// identically, with the API down.
import { CUSTOM_DEFAULTS, GRID, OVERLAYS, PRESETS } from './config'
import type { GridSpecEnum, GridSpecNum } from './config'
import type { LeverValue, ScenarioConfig } from './types'

function round10(v: number): number {
  return Math.round(v * 1e10) / 1e10
}

/** Python's `_snap`: parse + clamp to [lo, hi] + snap to the widget grid; null if unparseable. */
export function snap(raw: string, key: string): LeverValue | null {
  const spec = GRID[key]
  if (!spec) return null
  if (spec.type === 'bool') return raw === '1' || raw === 'true' || raw === 'True'
  if (spec.type === 'enum') return (spec as GridSpecEnum).values.includes(raw) ? raw : null
  const { lo, hi, step, type } = spec as GridSpecNum
  const f = Number(raw)
  if (raw.trim() === '' || Number.isNaN(f)) return null
  let v = Math.min(Math.max(f, lo), hi)
  const k = Math.round((v - lo) / step)
  v = round10(lo + k * step)
  v = Math.min(Math.max(v, lo), hi)          // snap can land one step past hi on odd grids
  return type === 'int' ? Math.round(v) : v
}

/** parse_query_config: query params → {preset, overlays, levers}; junk silently dropped. */
export function parseQuery(qp: Record<string, string>): ScenarioConfig {
  let preset: string | null = qp.preset ?? null
  if (preset != null && !PRESETS.some((p) => p.key === preset)) preset = null
  const ovKeys = OVERLAYS.map((o) => o.key)
  let overlays = String(qp.ov ?? '').split(',').filter((k) => ovKeys.includes(k))
  if (overlays.includes('cw-robot-tax') && overlays.includes('grt-robot-tax'))
    overlays = overlays.filter((k) => k !== 'grt-robot-tax')
  const levers: Record<string, LeverValue> = {}
  for (const key of Object.keys(GRID)) {
    if (key in qp) {
      const v = snap(qp[key], key)
      if (v !== null) levers[key] = v
    }
  }
  return { preset, overlays, levers }
}

/** Python's f"{v:g}" for the values our grids produce. */
export function pyG(v: number): string {
  if (v === 0) return '0'
  return String(Number(v.toPrecision(6)))
}

function isClose(a: number, b: number, absTol: number): boolean {
  return Math.abs(a - b) <= Math.max(1e-9 * Math.max(Math.abs(a), Math.abs(b)), absTol)
}

/** encode_query_config: preset + overlays + only the levers that differ from pristine. */
export function encodeQuery(
  presetKey: string | null,
  overlays: string[],
  current: Record<string, LeverValue>,
  pristine: Record<string, LeverValue>,
): Record<string, string> {
  const out: Record<string, string> = {}
  if (presetKey) out.preset = presetKey
  if (overlays.length) out.ov = overlays.join(',')
  for (const [key, spec] of Object.entries(GRID)) {
    if (!(key in current) || !(key in pristine)) continue
    const cur = current[key]
    const pri = pristine[key]
    if (spec.type === 'bool' || spec.type === 'enum') {
      if (cur !== pri) out[key] = spec.type === 'bool' ? (cur ? '1' : '0') : String(cur)
    } else {
      const { step, type } = spec as GridSpecNum
      if (!isClose(Number(cur), Number(pri), (step || 1) / 2.001)) {
        out[key] = type === 'float' ? pyG(Number(cur)) : String(Math.round(Number(cur)))
      }
    }
  }
  return out
}

/** The address-bar string for a config (diffs vs its own preset defaults). */
export function queryStringFor(cfg: ScenarioConfig): string {
  const pristineSource = cfg.preset
    ? PRESETS.find((p) => p.key === cfg.preset)?.defaults ?? CUSTOM_DEFAULTS
    : CUSTOM_DEFAULTS
  const current = { ...pristineSource, ...cfg.levers }
  const qp = encodeQuery(cfg.preset, cfg.overlays, current, pristineSource)
  return new URLSearchParams(qp).toString()
}

/** Session-start parse of location.search (the app's session-once URL arm). */
export function configFromLocation(search: string): ScenarioConfig {
  const qp: Record<string, string> = {}
  for (const [k, v] of new URLSearchParams(search)) qp[k] = v
  return parseQuery(qp)
}
