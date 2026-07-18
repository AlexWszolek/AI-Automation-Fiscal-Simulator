// Port of charts.tornado_chart semantics: horizontal signed bars, top levers by |spearman|,
// red = raising the lever worsens the deficit, blue = improves it.
import type { VisualizationSpec } from 'vega-embed'
import { TORNADO_LABELS } from './labels'
import { NEG, POS } from './vega'
import type { TornadoEntry } from '../lib/types'

export function tornado(entry: TornadoEntry, top = 12, stale = false): VisualizationSpec {
  const rows = [...entry.tornado]
    .sort((a, b) => Math.abs(b.spearman) - Math.abs(a.spearman))
    .slice(0, top)
    .map((t) => ({ lever: TORNADO_LABELS[t.lever] ?? t.lever, spearman: t.spearman }))
  return {
    data: { values: rows },
    mark: { type: 'bar', opacity: stale ? 0.35 : 1.0 },
    encoding: {
      y: { field: 'lever', type: 'nominal', sort: null, title: null, axis: { labelLimit: 0 } },
      x: { field: 'spearman', type: 'quantitative', title: 'rank correlation with the final-year deficit' },
      color: {
        condition: { test: 'datum.spearman > 0', value: NEG },
        value: POS,
        legend: null,
      },
    },
    width: 'container',
    height: Math.max(180, rows.length * 24),
  }
}
