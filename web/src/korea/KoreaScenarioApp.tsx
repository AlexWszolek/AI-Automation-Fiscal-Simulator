// The interactive Korea site (parity track): lever rail + preset picker driving the same
// payload function behind the static bundles and /api/korea/run. The presenter view at
// /korea.html stays untouched until this page graduates to the default Korea entry.
// ALL user-facing text is provisional until Alex's copy pass (copy.json → "korea").
import { Fragment, useEffect, useMemo, useReducer, useState } from 'react'
import { fundBand, compositionBars, koreaGeoMap } from '../charts/korea'
import { NEG, PALETTE } from '../charts/palette'
import { timeSeries } from '../charts/timeSeries'
import { ChartPanel } from '../components/ChartPanel'
import { ListBox } from '../components/ListBox'
import { ShareBox } from '../components/AboutModal'
import { SelectControl, SliderControl } from '../components/controls'
import {
  configFromLocation, effectiveKoreaLevers, fmt, INITIAL_KOREA, KOREA_GRID,
  KOREA_GROUPS, KOREA_PRESETS, queryStringFor,
  type KoreaConfig,
} from './config'
import { KoreaAbout } from './KoreaAbout'
import { LangToggle } from './LangToggle'
import { useLocale } from './locale'
import { KoreaTornadoSection } from './KoreaTornadoSection'
import { useKoreaScenarioData, type KoreaFundJson, type KoreaScenarioPayload } from './useKoreaScenarioData'


const WF_COLORS = ['#c9d7e4', '#d9a441', '#b3554d', '#5b7c99', '#7d6ca3', '#8f2a1d', '#b9b2a6']

type Action =
  | { type: 'setPreset'; preset: string }
  | { type: 'setLever'; key: string; value: number }
  | { type: 'reset' }

function reducer(cfg: KoreaConfig, a: Action): KoreaConfig {
  if (a.type === 'setPreset') return { preset: a.preset, levers: {} }
  if (a.type === 'reset') return { ...cfg, levers: {} }
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

type RevenueLine = NonNullable<KoreaScenarioPayload['revenue_lines']>[number]

// Revenue by source: the thesis as a table. Lines grouped by where the money lands, a
// subtotal per destination, and an all-levels net — signed, loss hue on losses.
function RevenueTable({ lines, copy, y0, y }:
                      { lines: RevenueLine[]; copy: any; y0: number; y: number }) {
  const rounded = (v: number) => Number(v.toFixed(1))
  const signed = (v: number) => { const r = rounded(v); return (r > 0 ? '+' : '') + (r === 0 ? '0.0' : r.toFixed(1)) }
  const tone = (v: number) => { const r = rounded(v); return r < 0 ? { color: 'var(--bad)' } : r > 0 ? { color: 'var(--good)' } : undefined }
  const groups: RevenueLine['dest'][] = ['funds', 'general', 'local']
  const sum = (ls: RevenueLine[], k: 'final_tn' | 'cum_tn') => ls.reduce((a, l) => a + l[k], 0)
  const shown = lines.filter((l) => l.kind !== 'transfer')
  const transfer = lines.find((l) => l.kind === 'transfer')
  return (
    <div className="col-wide revenue-table">
      <h2>{copy.title}</h2>
      <div className="table-scroll">
        <table className="data-table summary-table">
          <thead>
            <tr>
              <th>{copy.columns.line}</th>
              <th className="num">{copy.columns.baseline}</th>
              <th className="num">{copy.columns.mix}</th>
              <th className="num">{fmt(copy.columns.final, { y })}</th>
              <th className="num">{fmt(copy.columns.cum, { y0, y })}</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => {
              const ls = shown.filter((l) => l.dest === g)
              return (
                <Fragment key={g}>
                  <tr className="group-row"><td colSpan={5}>{copy.subtotals[g]}</td></tr>
                  {ls.map((l) => (
                    <tr key={l.key}>
                      <td className="row-label">{copy.lines[l.key] ?? l.key}</td>
                      <td className="num">{l.baseline_tn != null ? l.baseline_tn.toFixed(1) : '—'}</td>
                      <td className="num">{l.mix_pct != null ? `${l.mix_pct.toFixed(1)}%` : '—'}</td>
                      <td className="num" style={tone(l.final_tn)}>{signed(l.final_tn)}</td>
                      <td className="num" style={tone(l.cum_tn)}>{signed(l.cum_tn)}</td>
                    </tr>
                  ))}
                  {transfer && (g === 'funds' || g === 'general') && (
                    <tr key={`${g}-transfer`}>
                      <td className="row-label">{copy.lines.recapture_transfer}</td>
                      <td className="num">—</td>
                      <td className="num">—</td>
                      <td className="num" style={tone(g === 'funds' ? transfer.final_tn : -transfer.final_tn)}>
                        {signed(g === 'funds' ? transfer.final_tn : -transfer.final_tn)}</td>
                      <td className="num" style={tone(g === 'funds' ? transfer.cum_tn : -transfer.cum_tn)}>
                        {signed(g === 'funds' ? transfer.cum_tn : -transfer.cum_tn)}</td>
                    </tr>
                  )}
                  <tr className="emph">
                    <td className="row-label">{copy.subtotals[g]}</td>
                    <td className="num"></td>
                    <td className="num"></td>
                    <td className="num" style={tone(sum(ls, 'final_tn') + (transfer ? (g === 'funds' ? transfer.final_tn : g === 'general' ? -transfer.final_tn : 0) : 0))}>
                      {signed(sum(ls, 'final_tn') + (transfer ? (g === 'funds' ? transfer.final_tn : g === 'general' ? -transfer.final_tn : 0) : 0))}</td>
                    <td className="num" style={tone(sum(ls, 'cum_tn') + (transfer ? (g === 'funds' ? transfer.cum_tn : g === 'general' ? -transfer.cum_tn : 0) : 0))}>
                      {signed(sum(ls, 'cum_tn') + (transfer ? (g === 'funds' ? transfer.cum_tn : g === 'general' ? -transfer.cum_tn : 0) : 0))}</td>
                  </tr>
                </Fragment>
              )
            })}
            <tr className="emph">
              <td className="row-label">{copy.subtotals.net}</td>
              <td className="num"></td>
              <td className="num"></td>
              <td className="num" style={tone(sum(shown, 'final_tn'))}>{signed(sum(shown, 'final_tn'))}</td>
              <td className="num" style={tone(sum(shown, 'cum_tn'))}>{signed(sum(shown, 'cum_tn'))}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="caption">{copy.caption}</p>
    </div>
  )
}

// tone: 'bad' paints the value in the loss hue (tokens: red = fiscally bad); the demography
// figure stays ink because it is the published baseline, not automation's doing
function Metric({ label, value, ground, tone = 'bad' }:
                { label: string; value: string; ground: string; tone?: 'bad' | 'neutral' }) {
  return (
    <div className="metric hero">
      <div className="metric-label caption">{label}</div>
      <div className={tone === 'bad' ? 'metric-value num bad' : 'metric-value num'}>{value}</div>
      <div className="metric-ground caption">{ground}</div>
    </div>
  )
}

export default function KoreaScenarioApp() {
  const [cfg, dispatch] = useReducer(
    reducer,
    location.search && location.search !== '?' ? configFromLocation(location.search) : INITIAL_KOREA,
  )
  const { lang, setLang, pack } = useLocale()
  const KO = pack.KO
  const T = KO.templates as Record<string, string>
  const SL = KO.series_labels as Record<string, string>
  const AX = KO.axis_titles as Record<string, string>
  const variantLabel = (v: string) =>
    (KO.rail.demography_options as Record<string, string>)[
      ({ low: '-1', medium: '0', high: '1' } as Record<string, string>)[v]] ?? v
  const { payload, loading, apiDown, failed } = useKoreaScenarioData(cfg)
  const values = effectiveKoreaLevers(cfg)
  // the language rides the URL (locale.ts advertises ?lang= for shareable links), so the
  // rewrite below and the share box carry it; English stays implicit
  const qs = useMemo(() => {
    const base = queryStringFor(cfg)
    if (lang !== 'ko') return base
    return base ? `${base}&lang=ko` : 'lang=ko'
  }, [cfg, lang])
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    history.replaceState(null, '', qs ? `?${qs}` : location.pathname)
  }, [qs])

  const preset = pack.preset(cfg.preset)
  // the exposure-source note applies to every preset whose physical ramp is on (robot
  // exposure is the US measure); the diffusion trio runs cognitive-only and gets none
  const isAgi = Number(KOREA_PRESETS.find((p) => p.key === cfg.preset)?.defaults.physical_feasibility ?? 0) > 0
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
  const finalYear = (payload?.config.start_year ?? 2026) + (payload?.config.display_periods ?? 10) - 1
  const [regions, setRegions] = useState<import('../charts/korea').KoreaRegionRow[] | null>(null)
  const [topo, setTopo] = useState<object | null>(null)
  useEffect(() => {
    fetch('/data/korea.json').then((r) => (r.ok ? r.json() : null))
      .then((b) => setRegions(b?.regions ?? null)).catch(() => setRegions(null))
    fetch('/data/korea-sido-topo.json').then((r) => (r.ok ? r.json() : null))
      .then(setTopo).catch(() => setTopo(null))
  }, [])
  // the map does not depend on the levers: a stable spec identity keeps ChartPanel from
  // re-running vega over the topojson on every payload (a visible chunk of each lever's
  // latency was this re-parse, not the model)
  const mapSpec = useMemo(
    () => (regions && topo ? koreaGeoMap(regions, topo, { tips: KO.tooltips }) : null),
    [regions, topo, KO],
  )

  return (
    <div className="shell">
      <aside className={[ 'rail', drawerOpen ? 'open' : '', apiDown ? 'api-down' : '' ].join(' ').trim()}>
        <button type="button" className="mobile-bar" aria-expanded={drawerOpen}
                onClick={() => setDrawerOpen((o) => !o)}>
          <span className="mobile-bar-scenario">
            <span className="mobile-bar-chevron" aria-hidden>{drawerOpen ? '▴' : '▾'}</span>
            {' '}{T.scenario_word} · <span className="mobile-bar-preset">{preset.name}</span>
          </span>
          {payload && (
            <span className="mobile-bar-metric">
              <span className="num">{fmt(T.money_tn, { v: payload.final.ei_shortfall_tn.toFixed(1) })}</span>
              <span className="mobile-bar-metric-label">{T.mobile_metric_label}</span>
            </span>
          )}
        </button>
        <div className="rail-body">
          <LangToggle lang={lang} setLang={setLang} />
          <details className="group" open>
            <summary>{KO.rail.preset_heading}</summary>
            <div className="picker">
              <ListBox
                ariaLabel="Scenario preset"
                value={cfg.preset}
                options={KOREA_PRESETS.map((p) => ({ value: p.key, label: pack.preset(p.key).name }))}
                onChange={(v) => dispatch({ type: 'setPreset', preset: v })}
              />
              <p className="caption">{preset.blurb}</p>
              {isAgi && <p className="caption">{KO.rail.agi_disclosure}</p>}
            </div>
          </details>
          {KOREA_GROUPS.map((g) => (
            <details key={g} className="group" open={g === 'Automation & adoption'}>
              <summary>{pack.group(g)}</summary>
              {Object.entries(KOREA_GRID).filter(([, s]) => s.group === g).map(([k, spec]) => {
                const c = pack.lever(spec.copy)
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
          <ShareBox queryString={qs} labels={pack.shared} />
          <KoreaAbout copy={KO.about} disclosures={KO.disclosures}
                      conventions={payload ? (payload.final.demo_variant === 'medium'
                        ? T.conventions_medium
                        : fmt(T.conventions_offmedium, { variant: variantLabel(payload.final.demo_variant) }))
                        + ' ' + T.band_note : ''} />
        </div>
      </aside>

      <main className="content">
        <div className="col-wide">
          <h1>{KO.title}</h1>
          <p>{KO.intro}</p>
          {apiDown && <p className="panel caption warning api-banner" role="alert">{KO.rail.api_down}</p>}
          {payload && payload.config.modified_fields.length > 0 && (
            <p className="panel caption modified-note">
              {fmt(T.modified_note, { fields: payload.config.modified_fields.join(', ') })}
            </p>
          )}
        </div>

        {failed && (
          <p className="panel caption col-wide warning">{T.load_failed}</p>
        )}

        {payload && (
          <>
            <div className="col-wide">
              <div className="metric-row heroes korea-heroes">
                <Metric
                  label={KO.metrics.nps}
                  value={fmt(T.nps_value, { y: payload.funds.nps.eroded_date != null
                    ? Math.floor(payload.funds.nps.eroded_date) : (payload.funds.nps.published_depletion ?? '—') })}
                  ground={fmt(T.nps_ground, { pub: payload.funds.nps.published_depletion ?? '—',
                    v: yearsFmt(payload.final.nps_given_back) })}
                />
                <Metric
                  label={KO.metrics.nhi}
                  value={fmt(T.nhi_value, { v: yearsFmt(payload.final.nhi_years_forward) })}
                  ground={fmt(T.nhi_ground, { pub: payload.funds.nhi.published_depletion ?? '—',
                                              d: payload.funds.nhi.eroded_date ?? '—' })}
                />
                <Metric
                  label={KO.metrics.ei}
                  value={fmt(T.ei_value, { v: payload.final.ei_shortfall_tn.toFixed(1) })}
                  ground={fmt(T.ei_ground, { plan: payload.funds.ei.published[payload.funds.ei.published.length - 1].toFixed(1) })}
                />
              </div>
              <div className="metric-row korea-second-row">
                <Metric
                  tone="neutral"
                  label={KO.metrics.demography}
                  value={fmt(T.demo_value, { v: payload.final.demo_decline_pct.toFixed(1) })}
                  ground={fmt(T.demo_ground, { variant: variantLabel(payload.final.demo_variant),
                    y: payload.config.start_year + payload.config.display_periods - 1 })}
                />
                <Metric
                  label={KO.metrics.jobs}
                  value={fmt(T.jobs_value, { v: payload.final.jobs_lost_M.toFixed(2),
                    man: (payload.final.jobs_lost_M * 100).toFixed(0) })}
                  ground={fmt(T.jobs_ground, { pct: payload.final.employment_drop_pct.toFixed(1),
                    y: payload.config.start_year + payload.config.display_periods - 1 })}
                />
                <Metric
                  label={KO.metrics.unemployment}
                  value={fmt(T.u_value, { v: payload.final.u_uplift_pp.toFixed(1) })}
                  ground={fmt(T.u_ground, { base: payload.final.u_base_pct.toFixed(1) })}
                />
                <Metric
                  label={KO.metrics.inc_tax}
                  value={fmt(T.money_tn, { v: payload.final.inc_tax_lost_cum_tn.toFixed(1) })}
                  ground={fmt(T.inctax_ground, { y: payload.config.start_year + payload.config.display_periods - 1 })}
                />
                <Metric
                  label={KO.metrics.contrib}
                  value={fmt(T.money_tn, { v: payload.final.contrib_lost_cum_tn.toFixed(1) })}
                  ground={fmt(T.contrib_ground, { e: payload.final.ei_outlay_cum_tn.toFixed(1) })}
                />
              </div>
            </div>

            {payload.policy_readouts.length > 0 && (
              <div className="col-wide panel policy-readouts">
                {payload.policy_readouts.map((r) => {
                  const lever = pack.lever(`kr:${r.key}`)
                  if (r.key === 'vat_pp' && r.coverage_pct == null)
                    return (
                      <p key={r.key} className="caption">
                        <strong>{lever.label}</strong> — {fmt(T.vat_readout_nogap, {
                          v: r.revenue_final_tn?.toFixed(1) ?? '—' })}
                      </p>
                    )
                  if (r.key === 'vat_pp')
                    return (
                      <p key={r.key} className="caption">
                        <strong>{lever.label}</strong> — {fmt(T.vat_readout, {
                          v: r.revenue_final_tn?.toFixed(1) ?? '—',
                          pct: r.coverage_pct?.toFixed(0) ?? '—',
                          gap: r.deficit_widening_final_tn?.toFixed(1) ?? '—' })}
                      </p>
                    )
                  if (r.key === 'nps_mandate_share')
                    return (
                      <p key={r.key} className="caption">
                        <strong>{lever.label}</strong> — {fmt(T.nps_readout, {
                          v: r.flow_final_tn?.toFixed(1) ?? '—',
                          b: r.years_bought_back?.toFixed(2) ?? '—',
                          g: r.given_back_nopolicy?.toFixed(2) ?? '—' })}
                      </p>
                    )
                  return (
                    <p key={r.key} className="caption">
                      <strong>{lever.label}</strong> — {fmt(T.corp_readout, {
                        v: r.transfer_final_tn?.toFixed(1) ?? '—',
                        nps: r.nps_years_recovered?.toFixed(2) ?? '—',
                        nhi: r.nhi_years_recovered?.toFixed(2) ?? '—',
                        ei: r.ei_shortfall_recovered_tn?.toFixed(1) ?? '—',
                        cost: r.deficit_cost_final_tn?.toFixed(1) ?? '—' })}
                    </p>
                  )
                })}
              </div>
            )}

            <div className="col-wide chart-grid">
              <ChartPanel
                title={KO.sections.nps}
                spec={fundBand(toFund(payload.funds.nps), AX.reserves, KO.series, { tips: KO.tooltips })}
                caption={`${KO.captions.nps} — ${payload.funds.nps.source}`}
              />
              <ChartPanel
                title={KO.sections.nhi}
                spec={fundBand(toFund(payload.funds.nhi), AX.reserves, KO.series, { tips: KO.tooltips })}
                caption={`${KO.captions.nhi} — ${payload.funds.nhi.source}`}
              />
              <ChartPanel
                title={KO.sections.ei}
                spec={fundBand(toFund(payload.funds.ei), AX.reserves, KO.series, { height: 260, tips: KO.tooltips })}
                caption={`${KO.captions.ei} — ${payload.funds.ei.source}`}
              />
              <ChartPanel
                title={KO.sections.workforce}
                spec={timeSeries(rows, ['employed_M', 'on_ui_M', 'exhausted_M', 'reabsorbed_M',
                  'exited_M', 'induced_M', 'retired_M'], AX.workers, startYear,
                  { kind: 'area', stack: true, height: 300, colors: WF_COLORS,
                    totalLabel: SL.workforce_total, labels: SL })}
                caption={KO.captions.workforce}
              />
              <ChartPanel
                title={KO.sections.wages}
                spec={timeSeries(rows, ['W_survivor'], AX.wage_index, startYear,
                  { yZero: false, tooltipFormat: ',.4f', labels: SL })}
                caption={KO.captions.wages}
              />
              <ChartPanel
                title={KO.sections.budget}
                spec={timeSeries(budgetRows, ['fed_revenue_tn', 'fed_deficit_abs_tn'],
                  AX.tn_year, startYear, { labels: SL, colors: [PALETTE[0], NEG] })}
                caption={KO.captions.budget}
              />
              <ChartPanel
                title={KO.sections.composition}
                spec={compositionBars(payload.composition_2035, instLabel, { tips: KO.tooltips })}
                caption={KO.captions.composition}
              />
              <ChartPanel
                title={KO.sections.ei_outlay}
                spec={timeSeries(outlayRows, ['ei_outlay_tn'], AX.tn_year, startYear,
                  { kind: 'bar', height: 220, labels: SL, colors: [NEG] })}
                caption={KO.captions.ei_outlay}
              />
            </div>

            {mapSpec && (
              <div className="col-wide korea-map-section">
                <div className="korea-map-text">
                  <h2>{KO.sections.map}</h2>
                  <p className="caption">{KO.captions.map}</p>
                </div>
                <div className="korea-map-chart">
                  <ChartPanel spec={mapSpec} />
                </div>
              </div>
            )}

            {/* below the map, per Alex — the thesis as a table closes the page's content;
                the tornado stays last as the diagnostic. A bundle cached from before this table shipped has no revenue_lines */}
            {payload.revenue_lines && payload.revenue_lines.length > 0 && (
              <RevenueTable lines={payload.revenue_lines} copy={KO.revenue_table}
                            y0={payload.config.start_year} y={finalYear} />
            )}

            <KoreaTornadoSection cfg={cfg} pack={pack} />

          </>
        )}

        {loading && !payload && <p className="caption col-wide">{T.loading}</p>}
      </main>
    </div>
  )
}
