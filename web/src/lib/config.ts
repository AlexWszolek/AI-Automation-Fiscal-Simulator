// Config helpers over the generated grid — widget defaults, the app's clamp rules, slugs.
import gridJson from '../gen/grid.json'
import type { LeverValue, ScenarioConfig } from './types'

export interface GridSpecNum { type: 'int' | 'float'; lo: number; hi: number; step: number }
export interface GridSpecEnum { type: 'enum'; values: string[] }
export interface GridSpecBool { type: 'bool' }
export type GridSpec = GridSpecNum | GridSpecEnum | GridSpecBool

export interface PresetMeta {
  key: string
  name: string
  blurb: string
  start_year: number
  n_periods: number
  adoption_start: number
  adoption_end: number
  adoption_reach_year: number | null
  defaults: Record<string, LeverValue>
  override_fields: string[]
  provenance: Record<string, { text: string; value: string | null }>
}

export const GRID = gridJson.grid as unknown as Record<string, GridSpec>
export const CUSTOM_DEFAULTS = gridJson.custom_defaults as unknown as Record<string, LeverValue>
export const PRESETS = gridJson.presets as unknown as PresetMeta[]
export const OVERLAYS = gridJson.overlays as unknown as { key: string; name: string; blurb: string }[]

export function presetMeta(key: string | null): PresetMeta | null {
  return PRESETS.find((p) => p.key === key) ?? null
}

/** Widget defaults for a preset (or the Custom defaults). */
export function defaultsFor(preset: string | null): Record<string, LeverValue> {
  const p = presetMeta(preset)
  return { ...(p ? p.defaults : CUSTOM_DEFAULTS) }
}

/** The effective lever values: defaults overlaid with the user's diffs. */
export function effectiveLevers(cfg: ScenarioConfig): Record<string, LeverValue> {
  const d = defaultsFor(cfg.preset)
  for (const [k, v] of Object.entries(cfg.levers)) if (k in d) d[k] = v
  return d
}

/** The app's price-share clamp: price max = round(1 − retained, 2); ≤ 0 forces price to 0. */
export function priceMax(retained: number): number {
  return Math.round((1 - retained) * 100) / 100
}

/** The app's robot-tax bound: round(min(0.30, retained·(1−auto_cost)), 2); < 0.01 disables. */
export function ataxBound(retained: number, autoCost: number): number {
  return Math.round(Math.min(0.3, retained * (1 - autoCost)) * 100) / 100
}

export function survivorRemainder(retained: number, price: number): number {
  return Math.max(0, 1 - retained - price)
}

/** True when the config is a precomputed static bundle (no lever diffs from the defaults). */
export function isPristine(cfg: ScenarioConfig): boolean {
  return Object.keys(cfg.levers).length === 0
}

/** Static bundle slug — mirror of webpayload.slug (canonical overlay order). */
export function slugFor(cfg: ScenarioConfig): string {
  const base = cfg.preset ?? 'custom'
  const ovs = OVERLAYS.map((o) => o.key).filter((k) => cfg.overlays.includes(k))
  return ovs.length ? `${base}~${ovs.join('+')}` : base
}

export function startYearFor(preset: string | null): number {
  return presetMeta(preset)?.start_year ?? (gridJson.start_year_custom as number)
}
