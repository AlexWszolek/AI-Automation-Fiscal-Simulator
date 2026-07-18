// The fiscal summary: tax/channel/detailed views × $B / %-of-CBO-revenue units, bold
// subtotal/net rows, signed red/blue values, the scale-check line, CSV downloads.
// Copy and semantics are the app's; data comes precomputed in the payload.
import { useState } from 'react'
import copy from '../content/copy.json'
import { Markdown } from '../content/md'
import { toCsv, download } from '../lib/csv'
import { thousands, trueMinus } from '../lib/format'
import type { ScenarioPayload, SummaryView } from '../lib/types'
import { HelpTip } from './controls'

const PROSE = copy.prose as Record<string, string>
type ViewKey = 'tax' | 'channel' | 'detail'

function SummaryGrid({ v }: { v: SummaryView }) {
  return (
    <div className="table-scroll">
      <table className="data-table summary-table">
        <thead>
          <tr>
            <th>group</th>
            <th>label</th>
            {v.years.map((y) => <th key={y} className="num">{y}</th>)}
            <th className="num">Total</th>
          </tr>
        </thead>
        <tbody>
          {v.rows.map((r, i) => {
            const emph = r.kind === 'subtotal' || r.kind === 'net'
            const cell = (x: number | null, key: string | number) => (
              <td key={key} className="num"
                  style={x != null && x < -0.05 ? { color: 'var(--bad)' }
                    : x != null && x > 0.05 ? { color: 'var(--good)' } : undefined}>
                {x == null ? '' : trueMinus(x.toLocaleString('en-US', {
                  minimumFractionDigits: 1, maximumFractionDigits: 1 }))}
              </td>
            )
            return (
              <tr key={i} className={emph ? 'emph' : undefined}>
                <td>{r.group}</td>
                <td>{r.label}</td>
                {r.values.map((x, j) => cell(x, j))}
                {cell(r.total, 'total')}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export function SummaryTable({ payload }: { payload: ScenarioPayload }) {
  const [view, setView] = useState<ViewKey>('tax')
  const [pct, setPct] = useState(false)
  const sc = payload.scale_check
  const key = `${view === 'channel' ? 'channel' : 'tax'}_${pct ? 'pct' : 'busd'}` as const

  return (
    <section className="col-wide">
      <h2>Fiscal summary</h2>
      <div className="view-toggle">
        <HelpTip label="View" help={PROSE.view_help} />
        {(['tax', 'channel', 'detail'] as ViewKey[]).map((k) => (
          <label key={k}>
            <input type="radio" checked={view === k} onChange={() => setView(k)} />{' '}
            {k === 'tax' ? 'By tax category' : k === 'channel' ? 'By fiscal channel' : 'Detailed per-year'}
          </label>
        ))}
        {view !== 'detail' && (
          <>
            <span className="sep" />
            <HelpTip label="Units" help={PROSE.units_cbo_help} />
            <label>
              <input type="radio" checked={!pct} onChange={() => setPct(false)} /> $B
            </label>
            <label>
              <input type="radio" checked={pct} onChange={() => setPct(true)} />{' '}
              % of projected federal revenue (CBO)
            </label>
          </>
        )}
      </div>

      {view === 'detail' ? (
        <>
          <div className="table-scroll detail-scroll">
            <table className="data-table">
              <thead>
                <tr>{Object.keys(payload.rows[0]).map((c) => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {payload.rows.map((r, i) => (
                  <tr key={i}>
                    {Object.values(r).map((x, j) => (
                      <td key={j} className="num">
                        {typeof x === 'number' ? trueMinus(x.toLocaleString('en-US', {
                          maximumFractionDigits: 2 })) : String(x)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="caption">{PROSE.detail_caption}</p>
          <button className="dl" onClick={() => download('run-detail.csv', toCsv(payload.rows))}>
            Download full detail CSV
          </button>
        </>
      ) : (
        <>
          <div className="caption">
            <Markdown text={PROSE.summary_signs} />
          </div>
          <SummaryGrid v={payload.summary[key]} />
          {Math.abs(sc.add_pct) >= 1 && (
            <p className="caption">
              <strong>Scale check:</strong> in <span className="num">{sc.final_year}</span> this
              scenario {sc.add_pct > 0 ? 'adds' : 'removes'}{' '}
              <strong className="num">{thousands(Math.abs(sc.add_pct))}%</strong>{' '}
              {sc.add_pct > 0 ? 'to' : 'from'} CBO's projected{' '}
              {Math.min(sc.final_year, sc.cbo_max_year)} deficit
              (<span className="num">${thousands(sc.cbo_deficit_B)}B</span>) — on top of what CBO
              already projects.
              {sc.final_year > sc.cbo_max_year &&
                " (CBO's projections end at FY2036; the comparison holds their 2036 value.)"}
            </p>
          )}
          {pct && sc.extrapolated && (
            <p className="caption">
              % columns past FY{sc.cbo_max_year} extrapolate CBO revenue at the baseline's
              terminal growth rate.
            </p>
          )}
          <button className="dl" onClick={() => {
            const v = payload.summary[key]
            download('fiscal-summary.csv', toCsv(v.rows.map((r) => ({
              group: r.group, label: r.label, kind: r.kind,
              ...Object.fromEntries(r.values.map((x, i) => [v.years[i], x])),
              Total: r.total,
            }))))
          }}>
            Download summary CSV
          </button>
        </>
      )}
    </section>
  )
}
