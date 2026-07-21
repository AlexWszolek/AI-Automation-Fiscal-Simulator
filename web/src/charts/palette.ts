// Design-system constants for chart specs (mirror of tokens.css — vega cannot read CSS vars).
// Kept vega-free so spec builders stay in the main bundle while vega loads as its own chunk.
export const TOKENS = {
  ink: '#1a1a18',
  ink2: '#3d3d3a',
  ink3: '#6e6e68',
  line: '#e2dfd7',
  bad: '#8c2f28',
  good: '#5b7c99',
  serif: "Charter, 'Bitstream Charter', 'Charis SIL', 'XCharter', serif",
  mono: "'Source Code Pro', ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
} as const

export const PALETTE = ['#3b6ea5', '#d9a441', '#4e937a', '#b3554d', '#7d6ca3', '#6b7b8c', '#a98467']
export const NEG = TOKENS.bad
export const POS = TOKENS.good
