// The seminar screen (diplomat review, 2026-08): one 16:9 view with nothing below the fold —
// the map, four hero figures with icons, the pension chart, and a short preset arc. Presets
// ONLY: every number comes from the committed static bundles, so the screen works with the
// compute service down or on no network at all (the expert rail lives on /korea-app.html).
// Every string here is an existing copy.json key — no new copy (the slate and any gloss
// are Alex's).
import { useEffect, useMemo, useState } from 'react'
import { fundBand, koreaGeoMap, type KoreaRegionRow } from '../charts/korea'
import { ChartPanel } from '../components/ChartPanel'
import { fmt, KOREA_PRESETS } from './config'
import { LangToggle } from './LangToggle'
import { useLocale } from './locale'
import { useKoreaScenarioData, type KoreaFundJson } from './useKoreaScenarioData'

// PROPOSED seminar arc (Alex confirms the slate and its order): the central case, the
// forecasting community's median, and two fast worlds. Any KOREA_PRESETS key works.
const DASH_PRESETS = ['korea-central', 'korea-metaculus', 'korea-ai-2027', 'korea-agi-5y']

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

// small line icons in currentColor (the loss hue on the tiles) — design, not copy
const ICONS = {
  people: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <circle cx="9" cy="8" r="3.2" /><circle cx="17" cy="9" r="2.4" />
      <path d="M3 19c0-3.2 2.7-5.2 6-5.2s6 2 6 5.2M15.5 18.6c.4-2.3 2-3.8 4.5-3.8 1 0 1.8.3 2.5.8" />
    </svg>
  ),
  heart: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" />
      <path d="M5.5 12h3l1.5-2.5 2 5 1.5-2.5h4" />
    </svg>
  ),
  umbrella: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M3 12a9 9 0 0 1 18 0H3z" /><path d="M12 12v6a2 2 0 0 0 4 0" /><path d="M12 3v1.5" />
    </svg>
  ),
  pillars: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M3 9l9-5 9 5H3z" /><path d="M5 9v8M9.5 9v8M14.5 9v8M19 9v8" /><path d="M3 20h18" />
    </svg>
  ),
}

function Tile({ icon, label, value, ground }:
              { icon: keyof typeof ICONS; label: string; value: string; ground: string }) {
  return (
    <div className="dash-tile">
      <span className="dash-icon">{ICONS[icon]}</span>
      <div className="metric-label caption">{label}</div>
      <div className="metric-value num bad">{value}</div>
      <div className="metric-ground caption">{ground}</div>
    </div>
  )
}

function initialPreset(): string {
  const q = new URLSearchParams(location.search).get('preset')
  return q && KOREA_PRESETS.some((p) => p.key === q) ? q : DASH_PRESETS[0]
}

export default function KoreaDash() {
  const { lang, setLang, pack } = useLocale()
  const KO = pack.KO
  const T = KO.templates as Record<string, string>
  const AX = KO.axis_titles as Record<string, string>
  const [presetKey, setPresetKey] = useState(initialPreset)
  const cfg = useMemo(() => ({ preset: presetKey, levers: {} }), [presetKey])
  const { payload, loading, failed } = useKoreaScenarioData(cfg)
  const preset = pack.preset(presetKey)

  useEffect(() => {
    const q = new URLSearchParams(location.search)
    q.set('preset', presetKey)
    history.replaceState(null, '', `?${q.toString()}`)
  }, [presetKey])

  const [regions, setRegions] = useState<KoreaRegionRow[] | null>(null)
  const [topo, setTopo] = useState<object | null>(null)
  useEffect(() => {
    fetch('/data/korea.json').then((r) => (r.ok ? r.json() : null))
      .then((b) => setRegions(b?.regions ?? null)).catch(() => setRegions(null))
    fetch('/data/korea-sido-topo.json').then((r) => (r.ok ? r.json() : null))
      .then(setTopo).catch(() => setTopo(null))
  }, [])

  const arc = DASH_PRESETS.filter((k) => KOREA_PRESETS.some((p) => p.key === k))
  const finalYear = payload
    ? payload.config.start_year + payload.config.display_periods - 1 : 2035

  return (
    <div className="dash">
      <header className="dash-head">
        <h1>{KO.title}</h1>
        <nav className="dash-presets" aria-label={KO.rail.preset_heading}>
          {arc.map((k) => (
            <button key={k} type="button"
                    className={k === presetKey ? 'dash-preset active' : 'dash-preset'}
                    aria-pressed={k === presetKey}
                    onClick={() => setPresetKey(k)}>
              {pack.preset(k).name}
            </button>
          ))}
        </nav>
        <LangToggle lang={lang} setLang={setLang} />
      </header>
      <p className="dash-blurb caption">{preset.blurb}</p>

      {failed && <p className="panel caption warning">{T.bundle_failed}</p>}
      {loading && !payload && <p className="caption">{T.loading}</p>}

      {payload && (
        <div className="dash-body">
          <section className="dash-map">
            {regions && topo && (
              <ChartPanel spec={koreaGeoMap(regions, topo, { size: 500, tips: KO.tooltips })} />
            )}
            <h2>{KO.sections.map}</h2>
            <p className="caption">{KO.captions.map}</p>
          </section>

          <section className="dash-right">
            <div className="dash-tiles">
              <Tile icon="people" label={KO.metrics.jobs}
                    value={fmt(T.jobs_value, { v: payload.final.jobs_lost_M.toFixed(2),
                      man: (payload.final.jobs_lost_M * 100).toFixed(0) })}
                    ground={fmt(T.jobs_ground, { pct: payload.final.employment_drop_pct.toFixed(1),
                      y: finalYear })} />
              <Tile icon="heart" label={KO.metrics.nhi}
                    value={fmt(T.nhi_value, { v: yearsFmt(payload.final.nhi_years_forward) })}
                    ground={fmt(T.nhi_ground, { pub: payload.funds.nhi.published_depletion ?? '—',
                      d: payload.funds.nhi.eroded_date ?? '—' })} />
              <Tile icon="umbrella" label={KO.metrics.ei}
                    value={fmt(T.ei_value, { v: payload.final.ei_shortfall_tn.toFixed(1) })}
                    ground={fmt(T.ei_ground, {
                      plan: payload.funds.ei.published[payload.funds.ei.published.length - 1].toFixed(1) })} />
              <Tile icon="pillars" label={KO.metrics.nps}
                    value={fmt(T.nps_value, { v: yearsFmt(payload.final.nps_given_back) })}
                    ground={fmt(T.nps_ground, { d: payload.funds.nps.eroded_date ?? '—' })} />
            </div>
            <div className="dash-chart">
              <ChartPanel
                title={KO.sections.nps}
                spec={fundBand(toFund(payload.funds.nps), AX.reserves, KO.series,
                  { height: 300, tips: KO.tooltips })}
              />
            </div>
          </section>
        </div>
      )}

      <footer className="dash-foot caption">{T.deck_footer}</footer>
    </div>
  )
}
