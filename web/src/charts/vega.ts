// Shared vega-lite plumbing: one config object carrying the design system into every chart,
// a custom tooltip handler (site typography, not vega's default), and a mount helper.
// Charts are STATIC — no zoom/pan/actions; tooltips are the crosshair readout and the map.
import vegaEmbed, { type Result, type VisualizationSpec } from 'vega-embed'
import { TOKENS } from './palette'

export { NEG, PALETTE, POS, TOKENS } from './palette'

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
    symbolType: 'square',      // one symbol everywhere (user preference: squares, not circles)
  },
  view: { stroke: null },
} as const

// ---------------------------------------------------------------------- custom tooltip
// One shared floating card in the site's own typography: the FIRST entry ('State' or 'Year')
// becomes a bold header line; the rest render as label/value rows (labels serif, values mono).
let tipEl: HTMLDivElement | null = null

function tip(): HTMLDivElement {
  if (!tipEl) {
    tipEl = document.createElement('div')
    tipEl.className = 'site-tooltip'
    tipEl.style.display = 'none'
    document.body.appendChild(tipEl)
  }
  return tipEl
}

function esc(s: unknown): string {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function tooltipHandler(_handler: unknown, event: MouseEvent, _item: unknown, value: unknown) {
  const el = tip()
  if (value == null || value === '') {
    el.style.display = 'none'
    return
  }
  if (typeof value !== 'object') {
    el.innerHTML = `<div class="site-tooltip-head">${esc(value)}</div>`
  } else {
    const entries = Object.entries(value as Record<string, unknown>)
    let html = ''
    let rows = entries
    if (entries.length && (entries[0][0] === 'State' || entries[0][0] === 'Year')) {
      html += `<div class="site-tooltip-head">${esc(entries[0][1])}</div>`
      rows = entries.slice(1)
    }
    html += '<table>'
    for (const [k, v] of rows)
      html += `<tr><td class="k">${esc(k)}</td><td class="v">${esc(v)}</td></tr>`
    html += '</table>'
    el.innerHTML = html
  }
  el.style.display = 'block'
  const pad = 12
  const w = el.offsetWidth
  const h = el.offsetHeight
  let x = event.clientX + pad
  let y = event.clientY + pad
  if (x + w > window.innerWidth - 8) x = event.clientX - w - pad
  if (y + h > window.innerHeight - 8) y = event.clientY - h - pad
  el.style.left = `${x + window.scrollX}px`
  el.style.top = `${y + window.scrollY}px`
}

/** Render a spec into el. Returns the embed result for later .finalize(). */
export function mount(el: HTMLElement, spec: VisualizationSpec): Promise<Result> {
  return vegaEmbed(el, { ...spec, config: BASE_CONFIG } as VisualizationSpec, {
    actions: false,
    renderer: 'svg',
    tooltip: tooltipHandler,
  })
}
