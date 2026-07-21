// The page: lever rail (presets, responses, groups, share, about) + the content column
// (intro, metrics, charts, states, fiscal summary, tornado). Section order, chart set, and
// copy are the Streamlit app's; layout and type are DESIGN.md. The address bar always encodes
// the current configuration through the golden-pinned codec — old shared links resolve
// identically, with the API down.
import { useEffect, useMemo } from 'react'
import copy from './content/copy.json'
import { timeSeries } from './charts/timeSeries'
import { AboutSection, ShareBox } from './components/AboutModal'
import { ChartPanel } from './components/ChartPanel'
import { LeverPanel } from './components/LeverPanel'
import { MetricGrid } from './components/MetricGrid'
import { OverlayPicker, PresetPicker } from './components/Pickers'
import { StatesSection } from './components/StatesSection'
import { SummaryTable } from './components/SummaryTable'
import { TornadoSection } from './components/TornadoSection'
import { configFromLocation, queryStringFor } from './lib/codec'
import { effectiveLevers } from './lib/config'
import { thousands } from './lib/format'
import { INITIAL, useScenario } from './state/useScenario'
import { useScenarioData } from './state/useScenarioData'

const CAPTIONS = copy.captions as string[]
// Employed is ~90% of the area — the pale fill lets the distress bands carry the color
const WF_COLORS = ['#c9d7e4', '#d9a441', '#b3554d', '#5b7c99', '#7d6ca3', '#8f2a1d', '#b9b2a6']
const WAGE_CAPTION =
  'The wage index of workers who keep their jobs: raises funded from the survivor share push it ' +
  'up; labor-market slack (substitution) pulls it down.'
const WAGE_CAPTION_REAB = ' The re-employed line is the Baumol-vs-crowding tug of war on service wages.'

function initialConfig() {
  // a bare URL opens on the default scenario; ANY query param means the link decides
  if (!location.search || location.search === '?') return INITIAL
  return configFromLocation(location.search)
}

export default function App() {
  const [cfg, dispatch] = useScenario(initialConfig())
  const { payload, loading, apiDown, failed } = useScenarioData(cfg)
  const levers = effectiveLevers(cfg)
  const reabDynamics = Number(levers.reab_baumol) > 0 || Number(levers.reab_crowd) > 0
  const startYear = payload?.config.start_year ?? 2026
  const rows = payload?.rows ?? []
  const qs = useMemo(() => queryStringFor(cfg), [cfg])

  // the address bar always encodes the current configuration (replaceState never reloads)
  useEffect(() => {
    history.replaceState(null, '', qs ? `?${qs}` : location.pathname)
  }, [qs])

  return (
    <div className="shell">
      <aside className="rail">
        <PresetPicker cfg={cfg} dispatch={dispatch} />
        <OverlayPicker cfg={cfg} payload={payload} dispatch={dispatch} />
        <LeverPanel cfg={cfg} dispatch={dispatch} />
        <ShareBox queryString={qs} />
        <AboutSection />
      </aside>

      <main className="content">
        <div className="col-wide">
          <h1>Fiscal Consequences of AI Automation</h1>
          <p>{copy.intro}</p>
          {apiDown && (
            <p className="panel caption">
              Custom settings need the compute service, which is not reachable — showing the
              closest preset instead. Preset browsing works fully offline.
            </p>
          )}
          {payload && <MetricGrid p={payload} />}
          {payload && payload.config.modified_fields.length > 0 && (
            <p className="panel caption modified-note">
              ⚠️ sliders modified from the preset: {payload.config.modified_fields.join(', ')}
            </p>
          )}
          {payload?.warnings.kink_replaced && (
            <p className="caption">
              Adoption sliders moved: the preset's kinked path has been replaced by a linear ramp.
            </p>
          )}
          {payload?.warnings.ubi_unfunded && (
            <p className="panel caption warning">
              A ${thousands(payload.warnings.ubi_unfunded.ubi_annual)}/yr UBI requires a{' '}
              {thousands(100 * payload.warnings.ubi_unfunded.required_rate)}% average tax rate on
              the eroded base by the final year, and a required rate above 100% means the UBI
              cannot be funded from this base at all.
            </p>
          )}
        </div>

        {payload && rows.length > 0 && (
          <div className="col-wide chart-grid">
            <ChartPanel
              title="Where the workforce goes"
              spec={timeSeries(rows, ['employed_M', 'on_ui_M', 'exhausted_M', 'reabsorbed_M',
                'exited_M', 'induced_M', 'retired_M'], 'millions of workers', startYear,
                { kind: 'area', stack: true, height: 300, colors: WF_COLORS,
                  totalLabel: 'All workers (modeled)' })}
              caption={CAPTIONS[0]}
            />
            <ChartPanel
              title="Demand feedback — induced layoffs"
              spec={timeSeries(rows, ['induced_M'], 'millions of workers', startYear, { kind: 'area' })}
              caption={CAPTIONS[3]}
            />
            <ChartPanel
              title="Federal budget — absolute levels"
              spec={timeSeries(rows, ['fed_revenue_B', 'fed_deficit_abs_B'], '$ billions', startYear)}
              caption={CAPTIONS[1]}
            />
            <ChartPanel
              title="Wages of the still-employed"
              spec={timeSeries(rows, reabDynamics ? ['W_survivor', 'W_reab'] : ['W_survivor'],
                'wage index (1.0 = baseline)', startYear, { yZero: false, tooltipFormat: ',.4f' })}
              caption={WAGE_CAPTION + (reabDynamics ? WAGE_CAPTION_REAB : '')}
            />
            <ChartPanel
              title="What firms do with the saved wages"
              spec={timeSeries(rows, ['retained_profit_B', 'price_reduction_B', 'survivor_gains_B',
                'automation_spend_B'], '$ billions / year', startYear, { kind: 'bar', stack: true })}
              caption={CAPTIONS[2]}
            />
            <ChartPanel
              title="The raises in dollars"
              spec={timeSeries(rows, ['survivor_gain_fed_B', 'survivor_wage_cost_B'],
                '$ billions / year', startYear)}
              caption={CAPTIONS[4]}
            />
          </div>
        )}

        {payload && <StatesSection cfg={cfg} payload={payload} dispatch={dispatch} />}
        {payload && <SummaryTable payload={payload} />}
        {payload && <TornadoSection cfg={cfg} />}
        {loading && !payload && <p className="caption col-wide">Loading the scenario…</p>}
        <footer className="col-wide caption site-footer">
          Thanks to Princeton's Summer Social Impact Internship for funding my internship at
          Constellation Institute. Thanks to Jeff Alstott for mentoring and guiding me on this
          project.
        </footer>
        {failed && !payload && (
          <p className="panel caption col-wide warning">
            The scenario data could not be loaded — the site's data files are missing or
            unreachable. If this is a fresh deployment, the static bundles under /data were
            not copied.
          </p>
        )}
      </main>
    </div>
  )
}
