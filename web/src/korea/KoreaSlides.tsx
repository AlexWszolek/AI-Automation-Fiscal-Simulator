// The slide deck (workstream C): the Korea page's content recomposed at 16:9 slide
// dimensions — heroes + one big chart + sourcing per slide, enlarged type — per Alex's
// direction ("like the website ... but in the form of the dimensions of a slide"). NOT
// individual chart PNGs.
//
// Modes: bare URL = scrollable/keyboard preview (each slide scaled to fit the window);
// ?slide=N renders slide N alone at exactly 1920×1080 for headless-Chrome export
// (scripts/export_korea_slides.py → docs/research/korea-slides-pack/slides/).
// Data: the committed central scenario payload + korea.json (band + AGI overlay paths) +
// the n=400 tornado — the same numbers as the site, by construction.
import { useEffect, useMemo, useState } from 'react'
import type { VisualizationSpec } from 'vega-embed'
import { compositionBars, fundBand, koreaGeoMap, koreaTornado } from '../charts/korea'
import { timeSeries } from '../charts/timeSeries'
import { TORNADO_LABELS } from '../charts/labels'
import { ChartPanel } from '../components/ChartPanel'
import { fmt, KOREA_GRID, KOREA_PRESETS } from './config'
import { LangToggle } from './LangToggle'
import { useLocale } from './locale'
import type { KoreaFundJson, KoreaScenarioPayload } from './useKoreaScenarioData'



const SLIDE_W = 1920
const SLIDE_H = 1080

// vega type at presentation scale — applied over every spec on the deck
const SLIDE_VEGA_CONFIG = {
  axis: { labelFontSize: 20, titleFontSize: 22 },
  legend: { labelFontSize: 20, titleFontSize: 20 },
  text: { fontSize: 18 },
}

function slideSpec(spec: VisualizationSpec): VisualizationSpec {
  return { ...spec, config: SLIDE_VEGA_CONFIG } as VisualizationSpec
}

function toFund(f: KoreaFundJson) {
  return {
    years: f.years, published: f.published, eroded_central: f.eroded,
    eroded_lo: f.eroded_lo, eroded_hi: f.eroded_hi,
    published_depletion: f.published_depletion,
  }
}

interface KoreaBundle {
  headlines: any
  funds: any
  composition: any
}

function Hero({ label, value, ground }: { label: string; value: string; ground: string }) {
  return (
    <div className="metric hero slide-hero">
      <div className="metric-label caption">{label}</div>
      <div className="metric-value num">{value}</div>
      <div className="metric-ground caption">{ground}</div>
    </div>
  )
}

function useJson<T>(url: string): T | null {
  const [data, setData] = useState<T | null>(null)
  useEffect(() => {
    fetch(url).then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => setData(null))
  }, [url])
  return data
}

export default function KoreaSlides() {
  const { lang, setLang, pack } = useLocale()
  const KO = pack.KO
  const T = KO.templates as Record<string, string>
  const AX = KO.axis_titles as Record<string, string>
  const central = useJson<KoreaScenarioPayload>('/data/korea/scenarios/korea-central.json')
  const bundle = useJson<KoreaBundle>('/data/korea.json')
  const tornado = useJson<any>('/data/korea/tornado/korea-central.json')
  const topo = useJson<object>('/data/korea-sido-topo.json')
  const [allPresets, setAllPresets] = useState<Record<string, KoreaScenarioPayload> | null>(null)
  useEffect(() => {
    Promise.all(KOREA_PRESETS.map(async (p) => {
      const r = await fetch(`/data/korea/scenarios/${p.key}.json`)
      return [p.key, (await r.json()) as KoreaScenarioPayload] as const
    })).then((entries) => setAllPresets(Object.fromEntries(entries)))
      .catch(() => setAllPresets(null))
  }, [])

  const params = new URLSearchParams(location.search)
  const exportSlide = params.get('slide') ? Number(params.get('slide')) : null
  const [active, setActive] = useState(0)

  const ready = central && bundle && tornado && allPresets && topo
  const slides = useMemo(() => {
    if (!ready) return []
    const h = bundle!.headlines
    const f = central!.funds
    const scenarioRows = KOREA_PRESETS
      .filter((p) => allPresets![p.key])
      .map((p) => ({ p: { ...p, name: pack.preset(p.key).name }, pay: allPresets![p.key] }))
    const instLabel = (k: string) => KO.institutions[k] ?? k

    return [
      { key: 'headline', body: (
        <div className="slide-center">
          <h1>{KO.title}</h1>
          <p className="slide-intro">{KO.intro}</p>
          <div className="metric-row heroes korea-heroes slide-heroes">
            <Hero label={KO.metrics.nps}
                  value={fmt(T.p_nps_value, { v: h.nps.given_back_central.toFixed(1), n: h.nps.bought_years })}
                  ground={fmt(T.p_nps_ground, { lo: h.nps.given_back_lo.toFixed(1),
                    hi: h.nps.given_back_hi.toFixed(1), pre: h.nps.pre_reform_depletion,
                    pub: h.nps.published_depletion })} />
            <Hero label={KO.metrics.nhi}
                  value={fmt(T.nhi_value, { v: h.nhi.years_forward_central.toFixed(2) })}
                  ground={fmt(T.p_nhi_ground, { lo: h.nhi.years_forward_lo.toFixed(2),
                    hi: h.nhi.years_forward_hi.toFixed(2), pub: h.nhi.published_depletion })} />
            <Hero label={KO.metrics.ei}
                  value={fmt(T.ei_value, { v: h.ei.shortfall_central_tn.toFixed(1) })}
                  ground={fmt(T.p_ei_ground, { lo: h.ei.shortfall_lo_tn.toFixed(1),
                    hi: h.ei.shortfall_hi_tn.toFixed(1), plan: h.ei.planned_2029_tn.toFixed(1) })} />
          </div>
          <p className="caption slide-note">{KO.disclosure_note}</p>
        </div>
      ) },
      { key: 'nps', body: (
        <div className="slide-chart">
          <h2>{KO.sections.nps}</h2>
          <ChartPanel spec={slideSpec(fundBand(toFund(f.nps), AX.reserves,
            KO.series, { height: 640, tips: KO.tooltips }))} caption={`${KO.captions.nps} — ${f.nps.source}`} />
        </div>
      ) },
      { key: 'nhi', body: (
        <div className="slide-chart">
          <h2>{KO.sections.nhi}</h2>
          <ChartPanel spec={slideSpec(fundBand(toFund(f.nhi), AX.reserves,
            KO.series, { height: 640, tips: KO.tooltips }))} caption={`${KO.captions.nhi} — ${f.nhi.source}`} />
        </div>
      ) },
      { key: 'ei', body: (
        <div className="slide-chart slide-two-up">
          <h2>{KO.sections.ei}</h2>
          <div className="slide-cols">
            <ChartPanel spec={slideSpec(fundBand(toFund(f.ei), AX.reserves,
              KO.series, { height: 520, tips: KO.tooltips }))} caption={`${KO.captions.ei} — ${f.ei.source}`} />
            <ChartPanel spec={slideSpec(timeSeries(
              central!.ei_outlay_tn.map((v, i) => ({ period: i, ei_outlay_tn: v })),
              ['ei_outlay_tn'], AX.tn_year, 2026, { kind: 'bar', height: 520 }))}
              caption={KO.captions.ei_outlay} />
          </div>
        </div>
      ) },
      { key: 'scenarios', body: (
        <div className="slide-center">
          <h2>{KO.sections.scenarios ?? '[copy: Alex — scenarios slide title]'}</h2>
          <table className="slide-table num">
            <thead>
              <tr><th></th><th>{KO.metrics.nhi}</th><th>{KO.metrics.ei}</th><th>{KO.metrics.nps}</th></tr>
            </thead>
            <tbody>
              {scenarioRows.map(({ p, pay }) => (
                <tr key={p.key} className={p.key.includes('agi') ? 'agi-row' : ''}>
                  <td className="scenario-name">{p.name}</td>
                  <td>{pay.final.nhi_years_forward.toFixed(2)} yrs</td>
                  <td>₩{pay.final.ei_shortfall_tn.toFixed(1)}tn</td>
                  <td>{pay.final.nps_given_back.toFixed(2)} of 8</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="caption slide-note">{KO.rail.agi_disclosure}</p>
        </div>
      ) },
      { key: 'composition', body: (
        <div className="slide-chart">
          <h2>{KO.sections.composition}</h2>
          <ChartPanel spec={slideSpec(compositionBars(central!.composition_2035, instLabel,
            { height: 560, tips: KO.tooltips }))} caption={KO.captions.composition} />
        </div>
      ) },
      { key: 'map', body: (
        <div className="slide-chart">
          <h2>{KO.sections.map}</h2>
          <ChartPanel spec={slideSpec(koreaGeoMap((bundle as any).regions ?? [], topo!,
            { height: 620, tips: KO.tooltips }))} caption={KO.captions.map} />
        </div>
      ) },
      { key: 'sensitivity', body: (
        <div className="slide-chart">
          <h2>{KO.sections.tornado}</h2>
          <ChartPanel spec={slideSpec(koreaTornado(tornado!.targets.ei_shortfall_tn,
            (l: string) => (KOREA_GRID[l] ? pack.lever(KOREA_GRID[l].copy).label
                            : (TORNADO_LABELS[l] ?? l)),
            KO.tornado_targets.ei_shortfall_tn, { top: 9 }))}
            caption={`${KO.captions.tornado} — n=${tornado!.config.n}`} />
        </div>
      ) },
      { key: 'scope', body: (
        <div className="slide-center">
          <h2>{KO.sections.disclosures}</h2>
          <ul className="slide-list caption">
            {KO.disclosures.map((d: string, i: number) => <li key={i}>{d}</li>)}
          </ul>
          <p className="caption slide-note">Conventions: {central!.config.conventions}.</p>
        </div>
      ) },
    ]
  }, [ready, pack])

  useEffect(() => {
    if (exportSlide != null) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') setActive((a) => Math.min(a + 1, slides.length - 1))
      if (e.key === 'ArrowLeft') setActive((a) => Math.max(a - 1, 0))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [slides.length, exportSlide])

  if (!ready) return <p className="caption" style={{ padding: '2rem' }}>Loading the deck…</p>

  if (exportSlide != null) {
    const s = slides[exportSlide - 1]
    if (!s) return <p className="caption">No slide {exportSlide}</p>
    return (
      <div className="slide export" style={{ width: SLIDE_W, height: SLIDE_H }}>
        {s.body}
        <div className="slide-footer caption">
          <span>{T.deck_footer}</span>
          <span className="num">{exportSlide} / {slides.length}</span>
        </div>
      </div>
    )
  }

  const scale = Math.min(1, (window.innerWidth - 48) / SLIDE_W)
  return (
    <div className="deck">
      <p className="caption deck-help">{fmt(T.deck_help, { i: active + 1, n: slides.length })}</p>
      <LangToggle lang={lang} setLang={setLang} />
      <div className="slide-stage" style={{ width: SLIDE_W * scale, height: SLIDE_H * scale }}>
        <div className="slide" style={{ width: SLIDE_W, height: SLIDE_H,
                                        transform: `scale(${scale})` }}>
          {slides[active].body}
          <div className="slide-footer caption">
            <span>{T.deck_footer}</span>
            <span className="num">{active + 1} / {slides.length}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
