// The interactive Korea site (parity track): lever rail + preset picker driving the same
// payload function behind the static bundles and /api/korea/run. The presenter view at
// /korea.html stays untouched until this page graduates to the default Korea entry.
// ALL user-facing text is provisional until Alex's copy pass (copy.json → "korea").
import { useEffect, useMemo, useReducer, useState } from 'react'
import copy from '../content/copy.json'
import { fundBand, compositionBars, koreaGeoMap } from '../charts/korea'
import { timeSeries } from '../charts/timeSeries'
import { ChartPanel } from '../components/ChartPanel'
import { ListBox } from '../components/ListBox'
import { ShareBox } from '../components/AboutModal'
import { CheckboxControl, SelectControl, SliderControl } from '../components/controls'
import {
  configFromLocation, effectiveKoreaLevers, groupTitle, INITIAL_KOREA, KOREA_GRID,
  KOREA_GROUPS, KOREA_PRESETS, leverCopy, presetMeta, queryStringFor,
  type KoreaConfig,
} from './config'
import { KoreaTornadoSection } from './KoreaTornadoSection'
import { useKoreaScenarioData, type KoreaFundJson } from './useKoreaScenarioData'

const KO = (copy as any).korea
const WF_COLORS = ['#c9d7e4', '#d9a441', '#b3554d', '#5b7c99', '#7d6ca3', '#8f2a1d', '#b9b2a6']

type Action =
  | { type: 'setPreset'; preset: string }
  | { type: 'setLever'; key: string; value: number }
  | { type: 'toggleOverlay'; key: string }
  | { type: 'reset' }

function reducer(cfg: KoreaConfig, a: Action): KoreaConfig {
  if (a.type === 'setPreset') return { preset: a.preset, levers: {}, overlays: cfg.overlays }
  if (a.type === 'reset') return { ...cfg, levers: {}, overlays: [] }
  if (a.type === 'toggleOverlay')
    return {
      ...cfg,
      overlays: cfg.overlays.includes(a.key)
        ? cfg.overlays.filter((o) => o !== a.key)
        : [...cfg.overlays, a.key].sort(),
    }
  return { ...cfg, levers: { ...cfg.levers, [a.key]: a.value } }
}

function toFund(f: KoreaFundJson) {
  return {
    years: f.years, published: f.published, eroded_central: f.eroded,
    eroded_lo: f.eroded_lo, eroded_hi: f.eroded_hi,
    published_depletion: f.published_depletion,
  }
}

function yearsFmt(v: number) {
  return v.toFixed(v >= 1 ? 1 : 2)
}

function Metric({ label, value, ground }: { label: string; value: string; ground: string }) {
  return (
    <div className="metric hero">
      <div className="metric-label caption">{label}</div>
      <div className="metric-value num">{value}</div>
      <div className="metric-ground caption">{ground}</div>
    </div>
  )
}

export default function KoreaScenarioApp() {
  const [cfg, dispatch] = useReducer(
    reducer,
    location.search && location.search !== '?' ? configFromLocation(location.search) : INITIAL_KOREA,
  )
  const { payload, loading, apiDown, failed } = useKoreaScenarioData(cfg)
  const values = effectiveKoreaLevers(cfg)
  const qs = useMemo(() => queryStringFor(cfg), [cfg])
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    history.replaceState(null, '', qs ? `?${qs}` : location.pathname)
  }, [qs])

  const preset = presetMeta(cfg.preset)
  // ai-2027 shares the cognitive-only understatement even though its key lacks 'agi'
  const isAgi = ['korea-agi-20y', 'korea-agi-5y', 'korea-ai-2027'].includes(cfg.preset)
  const startYear = payload?.config.start_year ?? 2026
  const rows = payload?.rows ?? []
  const budgetRows = useMemo(
    () => rows.map((r) => ({
      ...r,
      fed_revenue_tn: r.fed_revenue_B / 1000,
      fed_deficit_abs_tn: r.fed_deficit_abs_B / 1000,
    })),
    [rows],
  )
  const outlayRows = useMemo(
    () => (payload?.ei_outlay_tn ?? []).map((v, i) => ({ period: i, ei_outlay_tn: v })),
    [payload],
  )
  const instLabel = (k: string) => KO.institutions[k] ?? k
  const [regions, setRegions] = useState<import('../charts/korea').KoreaRegionRow[] | null>(null)
  const [topo, setTopo] = useState<object | null>(null)
  useEffect(() => {
    fetch('/data/korea.json').then((r) => (r.ok ? r.json() : null))
      .then((b) => setRegions(b?.regions ?? null)).catch(() => setRegions(null))
    fetch('/data/korea-sido-topo.json').then((r) => (r.ok ? r.json() : null))
      .then(setTopo).catch(() => setTopo(null))
  }, [])

  return (
    <div className="shell">
      <aside className={drawerOpen ? 'rail open' : 'rail'}>
        <button type="button" className="mobile-bar" aria-expanded={drawerOpen}
                onClick={() => setDrawerOpen((o) => !o)}>
          <span className="mobile-bar-scenario">
            <span className="mobile-bar-chevron" aria-hidden>{drawerOpen ? '▴' : '▾'}</span>
            {' '}Scenario · <span className="mobile-bar-preset">{preset.name}</span>
          </span>
          {payload && (
            <span className="mobile-bar-metric">
              <span className="num">₩{payload.final.ei_shortfall_tn.toFixed(1)}tn</span>
              <span className="mobile-bar-metric-label">EI shortfall 2029</span>
            </span>
          )}
        </button>
        <div className="rail-body">
          <details className="group" open>
            <summary>{KO.rail.preset_heading}</summary>
            <div className="picker">
              <ListBox
                ariaLabel="Scenario preset"
                value={cfg.preset}
                options={KOREA_PRESETS.map((p) => ({ value: p.key, label: p.name }))}
                onChange={(v) => dispatch({ type: 'setPreset', preset: v })}
              />
              <p className="caption">{preset.blurb}</p>
              {isAgi && <p className="caption">{KO.rail.agi_disclosure}</p>}
            </div>
          </details>
          <details className="group" open>
            <summary>{KO.overlays.heading}</summary>
            {(['kr-vat', 'kr-nps-mandate'] as const).map((k) => (
              <CheckboxControl key={k} label={KO.overlays[k].label} help={KO.overlays[k].help}
                               value={cfg.overlays.includes(k)}
                               onChange={() => dispatch({ type: 'toggleOverlay', key: k })} />
            ))}
          </details>
          {KOREA_GROUPS.map((g) => (
            <details key={g} className="group" open={g === 'Automation & adoption'}>
              <summary>{groupTitle(g)}</summary>
              {Object.entries(KOREA_GRID).filter(([, s]) => s.group === g).map(([k, spec]) => {
                const c = leverCopy(k)
                if (spec.kind === 'select')
                  return (
                    <SelectControl key={k} label={c.label} help={c.help}
                                   values={(spec.values ?? []).map(String)}
                                   value={String(values[k])}
                                   display={k === 'demography_variant'
                                     ? KO.rail.demography_options : undefined}
                                   onChange={(v) => dispatch({ type: 'setLever', key: k, value: Number(v) })} />
                  )
                // the two JOINT constraints (the server clamps both): price is capped at
                // 1 − retained, and the robot tax at its retained-profit capacity bound
                const priceMax = k === 'price_reduction_share'
                  ? Math.max(0, 1 - Number(values.retained_profit_share))
                  : k === 'automation_tax_rate'
                    ? Math.max(0, Number(values.retained_profit_share)
                               * (1 - Number(values.auto_cost)))
                    : undefined
                return (
                  <SliderControl key={k} label={c.label} help={c.help}
                                 spec={{ lo: spec.lo, hi: spec.hi, step: spec.step ?? 0.01,
                                         type: spec.kind === 'int' ? 'int' : 'float' } as any}
                                 max={priceMax}
                                 value={priceMax !== undefined
                                   ? Math.min(Number(values[k]), priceMax) : Number(values[k])}
                                 onChange={(v) => dispatch({ type: 'setLever', key: k, value: v })} />
                )
              })}
            </details>
          ))}
          <ShareBox queryString={qs} />
        </div>
      </aside>

      <main className="content">
        <div className="col-wide">
          <p className="panel caption draft-banner">
            DRAFT — copy is ported/short-written pending Alex&apos;s review; numbers are
            final and test-pinned.
          </p>
          <h1>{KO.title}</h1>
          <p>{KO.intro}</p>
          <p className="panel caption">{KO.disclosure_note}</p>
          {apiDown && <p className="panel caption">{KO.rail.api_down}</p>}
          {payload && payload.config.modified_fields.length > 0 && (
            <p className="panel caption modified-note">
              ⚠️ levers modified from the preset: {payload.config.modified_fields.join(', ')}
            </p>
          )}
        </div>

        {failed && (
          <p className="panel caption col-wide warning">
            The Korea scenario bundles (/data/korea/scenarios) could not be loaded. If this
            is a fresh deployment, run scripts/gen_korea_scenarios.py and redeploy.
          </p>
        )}

        {payload && (
          <>
            <div className="col-wide">
              <div className="metric-row heroes korea-heroes">
                <Metric
                  label={KO.metrics.nps}
                  value={`${yearsFmt(payload.final.nps_given_back)} of 8 yrs`}
                  ground={`reform moved depletion 2057 → ${payload.funds.nps.published_depletion} · eroded ${payload.funds.nps.eroded_date ?? '—'}`}
                />
                <Metric
                  label={KO.metrics.nhi}
                  value={`${yearsFmt(payload.final.nhi_years_forward)} yrs earlier`}
                  ground={`published depletion ${payload.funds.nhi.published_depletion} · eroded ${payload.funds.nhi.eroded_date ?? '—'}`}
                />
                <Metric
                  label={KO.metrics.ei}
                  value={`₩${payload.final.ei_shortfall_tn.toFixed(1)}tn short`}
                  ground={`vs the planned ₩${payload.funds.ei.published[payload.funds.ei.published.length - 1].toFixed(1)}tn rebuild by 2029`}
                />
              </div>
              <div className="metric-row korea-second-row">
                <Metric
                  label={KO.metrics.demography}
                  value={`−${payload.final.demo_decline_pct.toFixed(1)}%`}
                  ground={`KOSIS ${payload.final.demo_variant} variant, by ${payload.config.start_year + payload.config.display_periods - 1} — automation's losses are measured on top of this path`}
                />
                <Metric
                  label={KO.metrics.jobs}
                  value={`${payload.final.jobs_lost_M.toFixed(2)}m jobs`}
                  ground={`${payload.final.employment_drop_pct.toFixed(1)}% of modeled wage employment by ${payload.config.start_year + payload.config.display_periods - 1}`}
                />
                <Metric
                  label={KO.metrics.unemployment}
                  value={`+${payload.final.u_uplift_pp.toFixed(1)} pp`}
                  ground={`on the ${payload.final.u_base_pct.toFixed(1)}% rate (2025H1) if displaced job-seekers count as unemployed`}
                />
                <Metric
                  label={KO.metrics.inc_tax}
                  value={`₩${payload.final.inc_tax_lost_cum_tn.toFixed(1)}tn`}
                  ground={`cumulative national + local income tax lost through ${payload.config.start_year + payload.config.display_periods - 1}`}
                />
                <Metric
                  label={KO.metrics.contrib}
                  value={`₩${payload.final.contrib_lost_cum_tn.toFixed(1)}tn`}
                  ground={`cumulative social-insurance contributions lost · EI benefits paid ₩${payload.final.ei_outlay_cum_tn.toFixed(1)}tn`}
                />
              </div>
            </div>

            {payload.overlay_readouts.length > 0 && (
              <div className="col-wide panel">
                {payload.overlay_readouts.map((r) => r.key === 'kr-vat' ? (
                  <p key={r.key} className="caption">
                    <strong>{KO.overlays['kr-vat'].label}</strong> — ₩{r.revenue_final_tn?.toFixed(1)}tn/yr
                    by the final year{r.coverage_pct != null &&
                      <> · covers {r.coverage_pct.toFixed(0)}% of the ₩{r.deficit_widening_final_tn?.toFixed(1)}tn widening</>}.
                    {' '}<span className="modified-note">{KO.overlays.vat_readout}</span>
                  </p>
                ) : (
                  <p key={r.key} className="caption">
                    <strong>{KO.overlays['kr-nps-mandate'].label}</strong> — ₩{r.flow_final_tn?.toFixed(1)}tn/yr
                    into the fund · buys back {r.years_bought_back?.toFixed(2)} of the {r.given_back_base?.toFixed(2)} given-back
                    years (depletion {r.eroded_date_with_mandate ?? '—'}).
                    {' '}<span className="modified-note">{KO.overlays.nps_readout}</span>
                  </p>
                ))}
              </div>
            )}

            <div className="col-wide chart-grid">
              <ChartPanel
                title={KO.sections.nps}
                spec={fundBand(toFund(payload.funds.nps), '₩ trillions, reserves', KO.series)}
                caption={`${KO.captions.nps} — ${payload.funds.nps.source}`}
              />
              <ChartPanel
                title={KO.sections.nhi}
                spec={fundBand(toFund(payload.funds.nhi), '₩ trillions, reserves', KO.series)}
                caption={`${KO.captions.nhi} — ${payload.funds.nhi.source}`}
              />
              <ChartPanel
                title={KO.sections.ei}
                spec={fundBand(toFund(payload.funds.ei), '₩ trillions, reserves', KO.series, { height: 260 })}
                caption={`${KO.captions.ei} — ${payload.funds.ei.source}`}
              />
              <ChartPanel
                title={KO.sections.workforce}
                spec={timeSeries(rows, ['employed_M', 'on_ui_M', 'exhausted_M', 'reabsorbed_M',
                  'exited_M', 'induced_M', 'retired_M'], 'millions of workers', startYear,
                  { kind: 'area', stack: true, height: 300, colors: WF_COLORS,
                    totalLabel: 'All workers (modeled)',
                    labels: { exited_M: 'Left labor force' } })}
                caption={KO.captions.workforce}
              />
              <ChartPanel
                title={KO.sections.wages}
                spec={timeSeries(rows, ['W_survivor'], 'wage index (1.0 = baseline)', startYear,
                  { yZero: false, tooltipFormat: ',.4f' })}
                caption={KO.captions.wages}
              />
              <ChartPanel
                title={KO.sections.budget}
                spec={timeSeries(budgetRows, ['fed_revenue_tn', 'fed_deficit_abs_tn'],
                  '₩ trillions / year', startYear)}
                caption={KO.captions.budget}
              />
              <ChartPanel
                title={KO.sections.composition}
                spec={compositionBars(payload.composition_2035, instLabel)}
                caption={KO.captions.composition}
              />
              {regions && topo && (
                <ChartPanel
                  title={KO.sections.map}
                  spec={koreaGeoMap(regions, topo)}
                  caption={KO.captions.map}
                />
              )}
              <ChartPanel
                title={KO.sections.ei_outlay}
                spec={timeSeries(outlayRows, ['ei_outlay_tn'], '₩ trillions / year', startYear,
                  { kind: 'bar', height: 220 })}
                caption={KO.captions.ei_outlay}
              />
            </div>

            <KoreaTornadoSection cfg={cfg} />

            <div className="col-wide panel korea-sources">
              <h2>{KO.sections.disclosures}</h2>
              <ul className="caption">
                {KO.disclosures.map((d: string, i: number) => <li key={i}>{d}</li>)}
              </ul>
              <p className="caption">
                Conventions: {payload.config.conventions}. {payload.band_note}.
              </p>
            </div>
          </>
        )}

        {loading && !payload && <p className="caption col-wide">Loading the scenario…</p>}
      </main>
    </div>
  )
}
