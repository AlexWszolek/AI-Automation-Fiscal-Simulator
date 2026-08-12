// Spec builders for the Korea page. Same design system as timeSeries.ts (tokens, axis
// conventions, bottom legends, crosshair-style hover), with the two Korea-specific forms:
// a fund-reserve chart (published path vs eroded central + uncertainty band) and
// horizontal bar comparisons for the institutional composition. Colors are the validated
// pair — published #3b6ea5 / eroded #8c2f28 (oxblood = the loss direction, as everywhere
// on the site) — and composition bars carry ONE hue: identity lives in the axis labels,
// so seven categorical hues would do no work (and the 7-slot palette fails CVD checks).
import type { VisualizationSpec } from 'vega-embed'
import { PALETTE, TOKENS } from './palette'

export interface KoreaFund {
  years: number[]
  published: number[]
  eroded_central: number[]
  eroded_lo: number[]
  eroded_hi: number[]
  published_depletion: number | null
}

const PUBLISHED_COLOR = PALETTE[0]          // #3b6ea5
const ERODED_COLOR = TOKENS.bad             // #8c2f28

export function fundBand(
  fund: KoreaFund,
  yTitle: string,
  labels: { published: string; eroded: string; band: string },
  opts: { height?: number } = {},
): VisualizationSpec {
  const { height = 300 } = opts
  const rows = fund.years.map((year, i) => ({
    year,
    published: fund.published[i],
    central: fund.eroded_central[i],
    lo: fund.eroded_lo[i],
    hi: fund.eroded_hi[i],
  }))
  const long = rows.flatMap((r) => [
    { year: r.year, series: labels.published, sidx: 0, value: r.published },
    { year: r.year, series: labels.eroded, sidx: 1, value: r.central },
  ])
  const n = fund.years.length
  const xEnc = {
    field: 'year', type: 'quantitative' as const, title: null,
    scale: { nice: false },
    axis: { tickCount: Math.min(n, 7), format: 'd', labelFlush: true, labelOverlap: 'parity' },
  }
  // the depletion line matters only for funds that approach zero — on a positive-only path
  // (EI's planned rebuild) it would just drag the axis down and flatten the real signal
  const minVal = Math.min(...fund.eroded_lo, ...fund.published)
  const maxVal = Math.max(...fund.published, ...fund.eroded_hi)
  const showZero = minVal < 0.25 * maxVal
  const zeroLayer = showZero
    ? [{
        data: { values: [{ zero: 0 }] },
        mark: { type: 'rule', stroke: TOKENS.ink3, strokeDash: [4, 4], strokeWidth: 1 },
        encoding: { y: { field: 'zero', type: 'quantitative' } },
      }]
    : []
  return {
    width: 'container', height, background: 'transparent',
    layer: [
      { // uncertainty envelope of the eroded path
        data: { values: rows },
        mark: { type: 'area', color: ERODED_COLOR, opacity: 0.13 },
        encoding: {
          x: xEnc,
          y: { field: 'lo', type: 'quantitative', title: yTitle, scale: { zero: false } },
          y2: { field: 'hi' },
        },
      },
      ...zeroLayer,
      {
        data: { values: long },
        mark: { type: 'line', strokeWidth: 2.5 },
        encoding: {
          x: xEnc,
          y: { field: 'value', type: 'quantitative', title: yTitle, scale: { zero: false } },
          color: {
            field: 'series', type: 'nominal', title: null,
            sort: [labels.published, labels.eroded],
            scale: { domain: [labels.published, labels.eroded],
                     range: [PUBLISHED_COLOR, ERODED_COLOR] },
            legend: { orient: 'bottom', columns: 1, labelLimit: 0 },
          },
        },
      },
      { // crosshair: nearest-year rule with all values in the tooltip
        data: { values: rows },
        mark: { type: 'rule', stroke: TOKENS.ink3, strokeWidth: 1, opacity: 0.6 },
        params: [{
          name: 'hov',
          select: { type: 'point', fields: ['year'], nearest: true,
                    on: 'pointerover', clear: 'pointerout' },
        }],
        encoding: {
          x: xEnc,
          opacity: { condition: { param: 'hov', empty: false, value: 0.6 }, value: 0 },
          tooltip: [
            { field: 'year', type: 'quantitative', title: 'Year', format: 'd' },
            { field: 'published', type: 'quantitative', title: labels.published, format: ',.1f' },
            { field: 'central', type: 'quantitative', title: labels.eroded, format: ',.1f' },
            { field: 'lo', type: 'quantitative', title: `${labels.band} (low)`, format: ',.1f' },
            { field: 'hi', type: 'quantitative', title: `${labels.band} (high)`, format: ',.1f' },
          ],
        },
      },
    ],
  } as VisualizationSpec
}

export function compositionBars(
  values: Record<string, number>,
  labelFor: (key: string) => string,
  opts: { height?: number } = {},
): VisualizationSpec {
  const rows = Object.entries(values).map(([k, v]) => ({ label: labelFor(k), value: v }))
  return {
    width: 'container', height: opts.height ?? 240, background: 'transparent',
    data: { values: rows },
    layer: [
      {
        mark: { type: 'bar', color: PUBLISHED_COLOR, cornerRadiusEnd: 3, height: { band: 0.7 } },
        encoding: {
          y: { field: 'label', type: 'nominal', title: null, sort: '-x',
               axis: { labelLimit: 220 } },
          x: { field: 'value', type: 'quantitative', title: null,
               axis: { format: '.0%', tickCount: 5 } },
          tooltip: [
            { field: 'label', type: 'nominal', title: 'Institution' },
            { field: 'value', type: 'quantitative', title: 'Base eroded', format: '.2%' },
          ],
        },
      },
      { // direct labels in ink, not series color (text wears text tokens)
        mark: { type: 'text', align: 'left', dx: 5, font: TOKENS.mono,
                fontSize: 11, color: TOKENS.ink2 },
        encoding: {
          y: { field: 'label', type: 'nominal', sort: '-x' },
          x: { field: 'value', type: 'quantitative' },
          text: { field: 'value', type: 'quantitative', format: '.1%' },
        },
      },
    ],
  } as VisualizationSpec
}

export function contrastBars(
  a: Record<string, number>,
  b: Record<string, number>,
  names: { a: string; b: string },
  labelFor: (key: string) => string,
  opts: { height?: number } = {},
): VisualizationSpec {
  const rows = [
    ...Object.entries(a).map(([k, v]) => ({ label: labelFor(k), scenario: names.a, value: v })),
    ...Object.entries(b).map(([k, v]) => ({ label: labelFor(k), scenario: names.b, value: v })),
  ]
  const order = [...new Set([...Object.keys(a), ...Object.keys(b)])].map(labelFor)
  return {
    width: 'container', height: opts.height ?? 300, background: 'transparent',
    data: { values: rows },
    mark: { type: 'bar', cornerRadiusEnd: 3 },
    encoding: {
      y: { field: 'label', type: 'nominal', title: null, sort: order,
           axis: { labelLimit: 220 } },
      yOffset: { field: 'scenario' },
      x: { field: 'value', type: 'quantitative', title: null,
           axis: { format: '.0%', tickCount: 5 } },
      color: {
        field: 'scenario', type: 'nominal', title: null,
        scale: { domain: [names.a, names.b], range: [PUBLISHED_COLOR, ERODED_COLOR] },
        legend: { orient: 'bottom', columns: 1, labelLimit: 0 },
      },
      tooltip: [
        { field: 'label', type: 'nominal', title: 'Institution' },
        { field: 'scenario', type: 'nominal', title: 'Scenario' },
        { field: 'value', type: 'quantitative', title: 'Base eroded', format: '.2%' },
      ],
    },
  } as VisualizationSpec
}

export function koreaTornado(
  rows: { lever: string; spearman: number }[],
  labelFor: (lever: string) => string,
  axisTitle: string,
  opts: { top?: number; stale?: boolean } = {},
): VisualizationSpec {
  // the US tornado's encoding (signed horizontal bars, red = raising the lever worsens
  // the headline), with Korea's own lever labels
  const top = [...rows]
    .sort((a, b) => Math.abs(b.spearman) - Math.abs(a.spearman))
    .slice(0, opts.top ?? 12)
    .map((t) => ({ lever: labelFor(t.lever), spearman: t.spearman }))
  return {
    data: { values: top },
    mark: { type: 'bar', opacity: opts.stale ? 0.35 : 1.0 },
    encoding: {
      y: { field: 'lever', type: 'nominal', sort: null, title: null,
           axis: { labelLimit: 0 } },
      x: { field: 'spearman', type: 'quantitative', title: axisTitle },
      color: {
        condition: { test: 'datum.spearman > 0', value: ERODED_COLOR },
        value: PUBLISHED_COLOR,
        legend: null,
      },
    },
    width: 'container',
    height: Math.max(180, top.length * 24),
  } as VisualizationSpec
}

export interface KoreaRegionRow {
  key: string
  short: string
  region: string
  col: number
  row: number
  emp_k: number
  helc_share: number
}

// the topojson carries the 2013 names; two provinces were renamed 2023–24
const TOPO_NAME: Record<string, string> = {
  강원특별자치도: '강원도', 전북특별자치도: '전라북도',
}

export function koreaGeoMap(rows: KoreaRegionRow[], topology: object,
                            opts: { height?: number } = {}): VisualizationSpec {
  // an actual boundary map (Statistics Korea SGIS census geometry via the
  // southkorea-maps kostat layer). Same sequential single-hue as the tile version;
  // names label the regions, values live in the tooltip and the legend.
  // no on-map labels: the audience knows its own provinces (Alex's review) — identity
  // rides the geography, values live in the tooltip and the legend
  const data = rows.filter((r) => r.col >= 0).map((r) => ({
    topo_name: TOPO_NAME[r.region] ?? r.region,
    region: r.region, pct: r.helc_share, emp_k: r.emp_k,
  }))
  return {
    width: 'container', height: opts.height ?? 520, background: 'transparent',
    data: { values: topology, format: { type: 'topojson', feature: 'skorea_provinces_geo' } },
    transform: [{
      lookup: 'properties.name',
      from: { data: { values: data }, key: 'topo_name',
              fields: ['region', 'pct', 'emp_k'] },
    }],
    projection: { type: 'mercator' },
    mark: { type: 'geoshape', stroke: '#fcfbf8', strokeWidth: 1.5 },
    encoding: {
      color: {
        field: 'pct', type: 'quantitative', title: null,
        scale: { range: ['#e9eff6', '#2a5480'] },
        legend: { orient: 'bottom', format: '.0%', gradientLength: 220 },
      },
      tooltip: [
        { field: 'region', type: 'nominal', title: 'Region' },
        { field: 'pct', type: 'quantitative', title: 'Displacement-prone share', format: '.1%' },
        { field: 'emp_k', type: 'quantitative', title: 'Employed (thousands)', format: ',.0f' },
      ],
    },
  } as VisualizationSpec
}
