// Port of the app's ts_chart, plus the crosshair readout: hovering anywhere on a chart snaps
// a rule to the nearest year and shows every series' value at that year (stacked charts also
// show the total). X axes run edge to edge (no nice-ing), with the first/last labels
// flush-aligned so they never squish; bar charts use a band axis so no phantom years appear.
import type { VisualizationSpec } from 'vega-embed'
import { LABELS } from './labels'
import { PALETTE } from './vega'

export interface TsOpts {
  kind?: 'line' | 'area' | 'bar'
  stack?: boolean
  height?: number
  colors?: string[]
  yZero?: boolean
  tooltipFormat?: string       // d3 number format for the crosshair values (default ',.1f')
  totalLabel?: string          // stacked charts: include the stack total in the crosshair
}

export function timeSeries(
  rows: Record<string, number>[],
  cols: string[],
  yTitle: string,
  startYear: number,
  opts: TsOpts = {},
): VisualizationSpec {
  const { kind = 'line', stack, height = 260, colors, yZero = true,
          tooltipFormat = ',.1f', totalLabel } = opts
  const labels = cols.map((c) => LABELS[c] ?? c)
  const long = rows.flatMap((r) =>
    cols.map((c, i) => ({
      year: startYear + (r.period as number),
      series: LABELS[c] ?? c,
      sidx: i,
      value: r[c],
    })),
  )
  const ordinalX = kind === 'bar'
  const xEnc = ordinalX
    ? { field: 'year', type: 'ordinal' as const, title: null, axis: { labelAngle: 0 } }
    : {
        field: 'year', type: 'quantitative' as const, title: null,
        scale: { nice: false },
        axis: { tickMinStep: 1, format: 'd', labelFlush: true, labelOverlap: 'parity' },
      }
  const mark =
    kind === 'line'
      ? { type: 'line' as const, strokeWidth: 2.5 }
      : kind === 'area'
        ? { type: 'area' as const, opacity: 0.85 }
        : { type: 'bar' as const }

  const markLayer = {
    mark,
    encoding: {
      x: xEnc,
      y: {
        field: 'value', type: 'quantitative' as const, title: yTitle,
        ...(stack !== undefined ? { stack } : {}),
        scale: { zero: yZero },
      },
      color: {
        field: 'series', type: 'nominal' as const, title: null,
        sort: labels,
        scale: { domain: labels, range: colors ?? PALETTE.slice(0, labels.length) },
        legend: { orient: 'bottom', columns: labels.length <= 2 ? 1 : 2, labelLimit: 0, symbolLimit: 0 },
      },
      ...(kind === 'area' ? { order: { field: 'sidx', type: 'quantitative' as const } } : {}),
    },
  }

  // the crosshair: pivot the long data to one row per year, hover snaps to the nearest rule
  const transforms: Record<string, unknown>[] = [
    { pivot: 'series', value: 'value', groupby: ['year'] },
  ]
  if (totalLabel) {
    transforms.push({
      calculate: labels.map((l) => `(isValid(datum['${l}']) ? datum['${l}'] : 0)`).join(' + '),
      as: totalLabel,
    })
  }
  const tooltipFields = [
    { field: 'year', type: 'nominal' as const, title: 'Year' },
    ...(totalLabel ? [{ field: totalLabel, type: 'quantitative' as const, title: totalLabel, format: tooltipFormat }] : []),
    ...labels.map((l) => ({ field: l, type: 'quantitative' as const, title: l, format: tooltipFormat })),
  ]
  const crosshairLayer = {
    transform: transforms,
    mark: { type: 'rule' as const, strokeWidth: 1 },
    params: [{
      name: 'hover',
      select: { type: 'point', fields: ['year'], nearest: true, on: 'pointermove', clear: 'pointerout' },
    }],
    encoding: {
      x: ordinalX
        ? { field: 'year', type: 'ordinal' as const }
        : { field: 'year', type: 'quantitative' as const },
      opacity: {
        condition: { param: 'hover', empty: false, value: 0.5 },
        value: 0,
      },
      color: { value: '#6e6e68' },
      tooltip: tooltipFields,
    },
  }

  return {
    data: { values: long },
    layer: [markLayer, crosshairLayer],
    width: 'container',
    height,
  } as unknown as VisualizationSpec
}
