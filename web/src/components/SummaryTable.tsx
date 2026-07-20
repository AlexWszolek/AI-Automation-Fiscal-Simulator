// The fiscal summary: tax/channel/detailed views × $B / %-of-CBO-revenue units, bold
// subtotal/net rows, signed red/blue values, the scale-check line, CSV downloads.
// Copy and semantics are the app's; data comes precomputed in the payload.
import { useState } from 'react'
import copy from '../content/copy.json'
import { LABELS } from '../charts/labels'
import { Markdown } from '../content/md'
import { toCsv, download } from '../lib/csv'
import { thousands, trueMinus } from '../lib/format'
import type { ScenarioPayload, SummaryView } from '../lib/types'
import { HelpTip } from './controls'

const PROSE = copy.prose as Record<string, string>
type ViewKey = 'tax' | 'channel' | 'detail'

function SummaryGrid({ v }: { v: SummaryView }) {
  // groups render as full-width divider rows, not a repeated left column
  const out: React.ReactNode[] = []
  let lastGroup = ''
  v.rows.forEach((r, i) => {
    if (r.group !== lastGroup) {
      lastGroup = r.group
      out.push(
        <tr key={`g${i}`} className="group-row">
          <td colSpan={v.years.length + 2}>{r.group}</td>
        </tr>,
      )
    }
    const emph = r.kind === 'subtotal' || r.kind === 'net'
    const cell = (x: number | null, key: string | number) => (
      <td key={key} className="num"
          style={x != null && x < -0.05 ? { color: 'var(--bad)' }
            : x != null && x > 0.05 ? { color: 'var(--good)' } : undefined}>
        {x == null ? '' : trueMinus(x.toLocaleString('en-US', {
          minimumFractionDigits: 1, maximumFractionDigits: 1 }))}
      </td>
    )
    out.push(
      <tr key={i} className={emph ? 'emph' : undefined}>
        <td className="row-label">{r.label}</td>
        {r.values.map((x, j) => cell(x, j))}
        {cell(r.total, 'total')}
      </tr>,
    )
  })
  return (
    <div className="table-scroll">
      <table className="data-table summary-table">
        <thead>
          <tr>
            <th>Line</th>
            {v.years.map((y) => <th key={y} className="num">{y}</th>)}
            <th className="num">Total</th>
          </tr>
        </thead>
        <tbody>{out}</tbody>
      </table>
    </div>
  )
}

export function SummaryTable({ payload }: { payload: ScenarioPayload }) {
  const [view, setView] = useState<ViewKey>('tax')
  const [pct, setPct] = useState(false)
  const sc = payload.scale_check
  const key = `${view === 'channel' ? 'channel' : 'tax'}_${pct ? 'pct' : 'busd'}` as const
  const cfgP = payload.config
  const csvStem = `fiscal-simulator-${cfgP.preset ?? 'custom'}-${cfgP.start_year}-${cfgP.start_year + cfgP.n_periods - 1}`
  const detailCols = Object.keys(payload.rows[0])

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
                <tr>
                  <th>Year</th>
                  {detailCols.map((c) => <th key={c} title={c}>{LABELS[c] ?? c}</th>)}
                </tr>
              </thead>
              <tbody>
                {payload.rows.map((r, i) => (
                  <tr key={i}>
                    <td className="num">{payload.config.start_year + (r.period as number)}</td>
                    {detailCols.map((c) => (
                      <td key={c} className="num">
                        {typeof r[c] === 'number' ? trueMinus(r[c].toLocaleString('en-US', {
                          maximumFractionDigits: 2 })) : String(r[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="caption">{PROSE.detail_caption}</p>
          <button className="dl" onClick={() => download(`${csvStem}-detail.csv`,
            toCsv(payload.rows.map((r) => ({
              year: payload.config.start_year + (r.period as number), ...r,
            }))))}>
            Download full detail CSV
          </button>
          <a className="dl" href="/data/column-guide.csv" download>Download the column guide</a>
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
            download(`${csvStem}-summary.csv`, toCsv(v.rows.map((r) => ({
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
