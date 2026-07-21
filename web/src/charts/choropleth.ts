// The states map: albersUsa geoshapes from the SELF-HOSTED topojson, colored by each state's
// OWN revenue at stake on a CONTINUOUS symlog gradient — the log-like ramp keeps 20% vs 50% vs
// 100% distinguishable instead of saturating past a top bin. Winner states (net gain) take the
// flat slate blue. Tooltips carry the dollar figures (the only tooltips on the site).
import type { VisualizationSpec } from 'vega-embed'
import type { StateRow } from '../lib/types'
import { POS, TOKENS } from './palette'

const TOOLTIP: [keyof StateRow, string, string][] = [
  ['revenue_loss_pct', 'Revenue lost (% of state receipts)', ',.1f'],
  ['net_B', 'Net position ($B, − = surplus)', ',.1f'],
  ['shortfall_B', 'Shortfall to close ($B)', ',.1f'],
  ['rate_hike_B', 'Closed by rate hikes ($B)', ',.1f'],
  ['spending_cut_B', 'Closed by spending cuts ($B)', ',.1f'],
  ['implied_rate_hike_pct', 'Implied rate hike (%)', ',.1f'],
]

export function choropleth(states: StateRow[]): VisualizationSpec {
  const dmax = Math.max(...states.map((s) => s.revenue_loss_pct), 1.0)
  return {
    data: {
      url: '/data/us-10m.json',
      format: { type: 'topojson', feature: 'states' },
    },
    transform: [
      {
        lookup: 'id',
        from: {
          data: { values: states as unknown as Record<string, unknown>[] },
          key: 'fips',
          fields: ['state', ...TOOLTIP.map(([f]) => f as string)],
        },
      },
      { filter: "isValid(datum['revenue_loss_pct'])" },
    ],
    mark: { type: 'geoshape', stroke: 'white', strokeWidth: 0.6 },
    encoding: {
      color: {
        condition: { test: "datum['revenue_loss_pct'] < 0", value: POS },
        field: 'revenue_loss_pct',
        type: 'quantitative',
        title: "Revenue lost (% of the state's own tax receipts)",
        scale: { type: 'symlog', constant: 2, domain: [0, dmax], range: ['#fbe6df', TOKENS.bad], clamp: true },
        legend: { orient: 'bottom', gradientLength: 280, labelLimit: 0, titleLimit: 0 },
      },
      tooltip: [
        { field: 'state', type: 'nominal', title: 'State' },
        ...TOOLTIP.map(([f, title, format]) => ({
          field: f as string, type: 'quantitative' as const, title, format,
        })),
      ],
    },
    projection: { type: 'albersUsa' },
    width: 'container',
    height: 420,
  }
}
