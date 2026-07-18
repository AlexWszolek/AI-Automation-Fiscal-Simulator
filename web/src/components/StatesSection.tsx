// The states section: prose, the three response controls (they live HERE, not the rail),
// the implied-rate headline, Map (default) / Table views, and the shortfall + closure charts.
// All copy is the app's (content/copy.json).
import { useState } from 'react'
import copy from '../content/copy.json'
import { choropleth } from '../charts/choropleth'
import { timeSeries } from '../charts/timeSeries'
import { thousands } from '../lib/format'
import type { ScenarioConfig, ScenarioPayload } from '../lib/types'
import type { ScenarioAction } from '../state/useScenario'
import { effectiveLevers } from '../lib/config'
import { ChartPanel } from './ChartPanel'
import { LeverRow } from './LeverPanel'
import { StateTable } from './StateTable'

const PROSE = copy.prose as Record<string, string>
const CAPTIONS = copy.captions as string[]

export function StatesSection({ cfg, payload, dispatch }: {
  cfg: ScenarioConfig
  payload: ScenarioPayload
  dispatch: (a: ScenarioAction) => void
}) {
  const [view, setView] = useState<'map' | 'table'>('map')
  const values = effectiveLevers(cfg)
  const f = payload.final
  const sc = payload.state_calc
  const rows = payload.rows
  const startYear = payload.config.start_year

  return (
    <section>
      <div className="col">
        <h2>The states — where the shock has no shock absorber</h2>
        <p>{PROSE.states_intro}</p>
        <div className="panel state-controls">
          <LeverRow k="state_resp" values={values} dispatch={dispatch} />
          <LeverRow k="state_cut" values={values} dispatch={dispatch} />
          <LeverRow k="rate_cap" values={values} dispatch={dispatch} />
        </div>
        {f.state_gap_B > 1 && (
          <p>
            Closing the final-year gap with taxes alone would mean raising state taxes roughly{' '}
            <span className="num">{thousands(sc.implied_pct, 1)}%</span> on everyone still
            working. That is what a <span className="num">${thousands(f.state_gap_B)}B</span>{' '}
            shortfall means against a <span className="num">${thousands(sc.tax_base_B)}B</span>{' '}
            remaining wage base, and <span className="num">{f.n_states_capped}</span> of 51
            states hit the rate-hike cap under the current response.
          </p>
        )}
        <div className="view-toggle">
          <label>
            <input type="radio" checked={view === 'map'} onChange={() => setView('map')} /> Map
          </label>
          <label>
            <input type="radio" checked={view === 'table'} onChange={() => setView('table')} /> Table
          </label>
        </div>
      </div>
      <div className="col-wide">
        {view === 'map' ? (
          <ChartPanel spec={choropleth(payload.states)} caption={PROSE.map_caption} />
        ) : (
          <>
            <StateTable states={payload.states} />
            <p className="caption">{PROSE.table_caption}</p>
          </>
        )}
        <div className="chart-grid">
          <ChartPanel
            spec={timeSeries(rows, ['state_gap_B', 'state_gap_cum_B'], '$ billions', startYear)}
            caption={CAPTIONS[5]}
          />
          <ChartPanel
            spec={timeSeries(rows, ['state_rate_hike_B', 'state_spending_cut_B'],
              '$ billions / year', startYear, { kind: 'bar', stack: true })}
            caption={CAPTIONS[6]}
          />
        </div>
      </div>
    </section>
  )
}
