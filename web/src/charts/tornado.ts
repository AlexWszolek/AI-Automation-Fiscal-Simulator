// Port of charts.tornado_chart semantics: horizontal signed bars, top levers by |spearman|,
// red = raising the lever worsens the deficit, blue = improves it.
import type { VisualizationSpec } from 'vega-embed'
import { TORNADO_LABELS } from './labels'
import { NEG, POS } from './palette'
import type { TornadoEntry } from '../lib/types'

export function tornado(entry: TornadoEntry, top = 12, stale = false,
                        compact = false): VisualizationSpec {
  // compact (small screens): truncate the ~35-char labels so the bars keep most of the width
  const rows = [...entry.tornado]
    .sort((a, b) => Math.abs(b.spearman) - Math.abs(a.spearman))
    .slice(0, compact ? Math.min(top, 10) : top)
    .map((t) => ({ lever: TORNADO_LABELS[t.lever] ?? t.lever, spearman: t.spearman }))
  return {
    data: { values: rows },
    mark: { type: 'bar', opacity: stale ? 0.35 : 1.0 },
    encoding: {
      y: { field: 'lever', type: 'nominal', sort: null, title: null,
           axis: { labelLimit: compact ? 118 : 0 } },
      x: { field: 'spearman', type: 'quantitative',
           title: compact ? 'rank correlation' : 'rank correlation with the final-year deficit' },
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
