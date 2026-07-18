// The per-state table (the map's fallback and detail view): all 51 rows sorted by shortfall,
// the app's column names, mono tabular numbers.
import { trueMinus } from '../lib/format'
import type { StateRow } from '../lib/types'

const COLS: [keyof StateRow, string][] = [
  ['net_B', 'Net position ($B, − = surplus)'],
  ['revenue_loss_pct', 'Revenue lost (% of state receipts)'],
  ['shortfall_B', 'Shortfall ($B)'],
  ['rate_hike_B', 'Rate hikes ($B)'],
  ['spending_cut_B', 'Spending cuts ($B)'],
  ['implied_rate_hike_pct', 'Implied rate hike (% of base)'],
]

export function StateTable({ states }: { states: StateRow[] }) {
  const sorted = [...states].sort((a, b) => b.shortfall_B - a.shortfall_B)
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>State</th>
            {COLS.map(([, label]) => <th key={label}>{label}</th>)}
            <th>Hit rate cap</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((s) => (
            <tr key={s.state}>
              <td>{s.state}</td>
              {COLS.map(([k]) => (
                <td key={k} className="num">{trueMinus((s[k] as number).toLocaleString('en-US', {
                  minimumFractionDigits: 1, maximumFractionDigits: 1 }))}</td>
              ))}
              <td>{s.at_cap ? '✓' : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
