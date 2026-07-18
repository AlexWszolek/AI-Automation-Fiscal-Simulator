// Shared vega-lite plumbing: one config object carrying the design system into every chart,
// and a mount helper. Charts are STATIC — no zoom/pan/actions; tooltips only where a spec
// explicitly encodes them (the map).
import vegaEmbed, { type Result, type VisualizationSpec } from 'vega-embed'

// Mirror of tokens.css (vega cannot read CSS custom properties).
export const TOKENS = {
  ink: '#1a1a18',
  ink2: '#3d3d3a',
  ink3: '#6e6e68',
  line: '#e2dfd7',
  bad: '#8c2f28',
  good: '#5b7c99',
  serif: "'Times New Roman', Times, 'Liberation Serif', Tinos, serif",
  mono: "ui-monospace, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace",
} as const

// Chart series palette — transitional 7-color set carried over from the Streamlit app;
// converging on red/blue/ink as charts adopt the semantic rule.
export const PALETTE = ['#3b6ea5', '#d9a441', '#4e937a', '#b3554d', '#7d6ca3', '#6b7b8c', '#a98467']
export const NEG = TOKENS.bad
export const POS = TOKENS.good

export const BASE_CONFIG = {
  background: 'transparent',
  font: TOKENS.serif,
  axis: {
    labelFont: TOKENS.mono,
    labelColor: TOKENS.ink3,
    labelFontSize: 11,
    titleFont: TOKENS.serif,
    titleColor: TOKENS.ink3,
    titleFontSize: 12,
    gridColor: TOKENS.line,
    domainColor: TOKENS.line,
    tickColor: TOKENS.line,
  },
  legend: {
    labelFont: TOKENS.serif,
    labelColor: TOKENS.ink2,
    labelFontSize: 12,
    titleFont: TOKENS.serif,
    titleColor: TOKENS.ink3,
    labelLimit: 0,
    symbolLimit: 0,
    titleLimit: 0,
  },
  view: { stroke: null },
} as const

/** Render a spec into el. Returns the embed result for later .finalize(). */
export function mount(el: HTMLElement, spec: VisualizationSpec): Promise<Result> {
  return vegaEmbed(el, { ...spec, config: BASE_CONFIG } as VisualizationSpec, {
    actions: false,
    renderer: 'svg',
  })
}
