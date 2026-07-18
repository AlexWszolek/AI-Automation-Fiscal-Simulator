// Port of the app's ts_chart: static multi-series time chart, calendar x-axis, labeled series,
// legend below, palette by position (or an explicit override). Same encodings as the altair
// original — the side-by-side screenshot is the acceptance gate.
import type { VisualizationSpec } from 'vega-embed'
import { LABELS } from './labels'
import { PALETTE } from './vega'

export interface TsOpts {
  kind?: 'line' | 'area' | 'bar'
  stack?: boolean
  height?: number
  colors?: string[]
  yZero?: boolean
}

export function timeSeries(
  rows: Record<string, number>[],
  cols: string[],
  yTitle: string,
  startYear: number,
  opts: TsOpts = {},
): VisualizationSpec {
  const { kind = 'line', stack, height = 260, colors, yZero = true } = opts
  const labels = cols.map((c) => LABELS[c] ?? c)
  const long = rows.flatMap((r) =>
    cols.map((c) => ({ year: startYear + (r.period as number), series: LABELS[c] ?? c, value: r[c] })),
  )
  const mark =
    kind === 'line'
      ? { type: 'line' as const, strokeWidth: 2.5 }
      : kind === 'area'
        ? { type: 'area' as const, opacity: 0.85 }
        : { type: 'bar' as const }
  const spec: VisualizationSpec = {
    data: { values: long },
    mark,
    encoding: {
      x: { field: 'year', type: 'quantitative', title: null, axis: { tickMinStep: 1, format: 'd' } },
      y: {
        field: 'value',
        type: 'quantitative',
        title: yTitle,
        ...(stack !== undefined ? { stack } : {}),
        scale: { zero: yZero },
      },
      color: {
        field: 'series',
        type: 'nominal',
        title: null,
        sort: labels,
        scale: { domain: labels, range: colors ?? PALETTE.slice(0, labels.length) },
        legend: { orient: 'bottom', columns: labels.length <= 2 ? 1 : 2, labelLimit: 0, symbolLimit: 0 },
      },
      ...(kind === 'area' ? { order: { field: 'color_series_sort_index', type: 'quantitative' } } : {}),
    },
    width: 'container',
    height,
  }
  return spec
}
