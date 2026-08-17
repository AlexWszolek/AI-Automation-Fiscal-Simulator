// Korea scenario config: preset + lever overrides, spec'd by the generated korea_grid.json
// (bounds/defaults come from the same Python the API sanitizes with — a slider cannot emit
// a value the server would clamp differently). URL form is plain query params
// (?preset=korea-fast&ui_weeks=39): no packed codec until share-link volume earns one.
import copy from '../content/copy.json'
import grid from '../gen/korea_grid.json'

export interface KoreaLeverSpec {
  lo: number
  hi: number
  copy: string
  group: string
  kind: 'float' | 'int' | 'select'
  step?: number
  values?: number[]
}
export interface KoreaPreset {
  key: string
  name: string
  blurb: string
  display_periods: number
  defaults: Record<string, number>
}
export interface KoreaConfig {
  preset: string
  levers: Record<string, number>       // only DEVIATIONS from the preset defaults
  overlays: string[]                   // active policy overlays (kr-vat, kr-nps-mandate)
}

export const KOREA_GRID = grid.levers as Record<string, KoreaLeverSpec>
export const KOREA_PRESETS = grid.presets as KoreaPreset[]
export const KOREA_GROUPS = grid.groups as string[]
export const KOREA_OVERLAY_KEYS = ['kr-vat', 'kr-nps-mandate'] as const
export const INITIAL_KOREA: KoreaConfig = { preset: 'korea-central', levers: {}, overlays: [] }

const KO = copy.korea as Record<string, any>
const US_LEVER_COPY = copy.levers as Record<string, { label: string; help: string | null }>

export function presetMeta(key: string): KoreaPreset {
  return KOREA_PRESETS.find((p) => p.key === key) ?? KOREA_PRESETS[1]
}

export function leverCopy(name: string): { label: string; help: string | null } {
  const ref = KOREA_GRID[name].copy
  if (ref.startsWith('us:')) return US_LEVER_COPY[ref.slice(3)]
  const kr = (KO.rail?.levers ?? {})[ref.slice(3)]
  return kr ?? { label: name, help: null }
}

export function groupTitle(g: string): string {
  return g === 'KOREA_AXES' ? String(KO.rail?.axes_group ?? g) : g
}

/** Preset defaults with the user's deviations applied. */
export function effectiveKoreaLevers(cfg: KoreaConfig): Record<string, number> {
  return { ...presetMeta(cfg.preset).defaults, ...cfg.levers }
}

export function isPristine(cfg: KoreaConfig): boolean {
  const d = presetMeta(cfg.preset).defaults
  return cfg.overlays.length === 0
    && Object.entries(cfg.levers).every(([k, v]) => v === d[k])
}

/** Only deviations reach the URL and the API body. */
export function deviations(cfg: KoreaConfig): Record<string, number> {
  const d = presetMeta(cfg.preset).defaults
  return Object.fromEntries(Object.entries(cfg.levers).filter(([k, v]) => v !== d[k]))
}

export function queryStringFor(cfg: KoreaConfig): string {
  const qp = new URLSearchParams()
  if (cfg.preset !== INITIAL_KOREA.preset) qp.set('preset', cfg.preset)
  if (cfg.overlays.length) qp.set('ov', [...cfg.overlays].sort().join(','))
  for (const [k, v] of Object.entries(deviations(cfg))) qp.set(k, String(v))
  return qp.toString()
}

export function configFromLocation(search: string): KoreaConfig {
  const qp = new URLSearchParams(search)
  const preset = qp.get('preset') ?? INITIAL_KOREA.preset
  const cfg: KoreaConfig = {
    preset: KOREA_PRESETS.some((p) => p.key === preset) ? preset : INITIAL_KOREA.preset,
    levers: {},
    overlays: (qp.get('ov') ?? '').split(',')
      .filter((o): o is (typeof KOREA_OVERLAY_KEYS)[number] =>
        (KOREA_OVERLAY_KEYS as readonly string[]).includes(o))
      .sort(),
  }
  for (const [k, raw] of qp.entries()) {
    const spec = KOREA_GRID[k]
    if (!spec) continue
    const x = Number(raw)
    if (!Number.isFinite(x)) continue
    let v = Math.min(Math.max(x, spec.lo), spec.hi)
    if (spec.kind === 'select' && spec.values)
      v = spec.values.reduce((a, b) => (Math.abs(b - x) < Math.abs(a - x) ? b : a))
    if (spec.kind === 'int') v = Math.round(v)
    cfg.levers[k] = v
  }
  return cfg
}

/** Tiny template formatter for the copy templates: fmt("{v} of 8 yrs", {v: '1.1'}). */
export function fmt(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? ''))
}
