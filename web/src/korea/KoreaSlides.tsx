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
import copy from '../content/copy.json'
import { compositionBars, fundBand, koreaTileMap, koreaTornado } from '../charts/korea'
import { timeSeries } from '../charts/timeSeries'
import { TORNADO_LABELS } from '../charts/labels'
import { ChartPanel } from '../components/ChartPanel'
import { KOREA_GRID, KOREA_PRESETS, leverCopy } from './config'
import type { KoreaFundJson, KoreaScenarioPayload } from './useKoreaScenarioData'

const KO = (copy as any).korea

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
  const central = useJson<KoreaScenarioPayload>('/data/korea/scenarios/korea-central.json')
  const bundle = useJson<KoreaBundle>('/data/korea.json')
  const tornado = useJson<any>('/data/korea/tornado/korea-central.json')
  const presetFinals = useJson<KoreaScenarioPayload>('/data/korea/scenarios/korea-agi-20y.json')
  const agi5 = useJson<KoreaScenarioPayload>('/data/korea/scenarios/korea-agi-5y.json')
  const slow = useJson<KoreaScenarioPayload>('/data/korea/scenarios/korea-slow.json')
  const fast = useJson<KoreaScenarioPayload>('/data/korea/scenarios/korea-fast.json')

  const params = new URLSearchParams(location.search)
  const exportSlide = params.get('slide') ? Number(params.get('slide')) : null
  const [active, setActive] = useState(0)

  const ready = central && bundle && tornado && presetFinals && agi5 && slow && fast
  const slides = useMemo(() => {
    if (!ready) return []
    const h = bundle!.headlines
    const f = central!.funds
    const scenarioRows = [
      { p: KOREA_PRESETS[0], pay: slow! }, { p: KOREA_PRESETS[1], pay: central! },
      { p: KOREA_PRESETS[2], pay: fast! }, { p: KOREA_PRESETS[3], pay: presetFinals! },
      { p: KOREA_PRESETS[4], pay: agi5! },
    ]
    const instLabel = (k: string) => KO.institutions[k] ?? k

    return [
      { key: 'headline', body: (
        <div className="slide-center">
          <h1>{KO.title}</h1>
          <p className="slide-intro">{KO.intro}</p>
          <div className="metric-row heroes korea-heroes slide-heroes">
            <Hero label={KO.metrics.nps}
                  value={`${h.nps.given_back_central.toFixed(1)} of ${h.nps.bought_years} yrs`}
                  ground={`band ${h.nps.given_back_lo.toFixed(1)}–${h.nps.given_back_hi.toFixed(1)} · reform moved depletion ${h.nps.pre_reform_depletion} → ${h.nps.published_depletion}`} />
            <Hero label={KO.metrics.nhi}
                  value={`${h.nhi.years_forward_central.toFixed(2)} yrs earlier`}
                  ground={`band ${h.nhi.years_forward_lo.toFixed(2)}–${h.nhi.years_forward_hi.toFixed(2)} · published depletion ${h.nhi.published_depletion}`} />
            <Hero label={KO.metrics.ei}
                  value={`₩${h.ei.shortfall_central_tn.toFixed(1)}tn short`}
                  ground={`band ₩${h.ei.shortfall_lo_tn.toFixed(1)}–${h.ei.shortfall_hi_tn.toFixed(1)}tn vs the planned ₩${h.ei.planned_2029_tn.toFixed(1)}tn rebuild by 2029`} />
          </div>
          <p className="caption slide-note">{KO.disclosure_note}</p>
        </div>
      ) },
      { key: 'nps', body: (
        <div className="slide-chart">
          <h2>{KO.sections.nps}</h2>
          <ChartPanel spec={slideSpec(fundBand(toFund(f.nps), '₩ trillions, reserves',
            KO.series, { height: 640 }))} caption={`${KO.captions.nps} — ${f.nps.source}`} />
        </div>
      ) },
      { key: 'nhi', body: (
        <div className="slide-chart">
          <h2>{KO.sections.nhi}</h2>
          <ChartPanel spec={slideSpec(fundBand(toFund(f.nhi), '₩ trillions, reserves',
            KO.series, { height: 640 }))} caption={`${KO.captions.nhi} — ${f.nhi.source}`} />
        </div>
      ) },
      { key: 'ei', body: (
        <div className="slide-chart slide-two-up">
          <h2>{KO.sections.ei}</h2>
          <div className="slide-cols">
            <ChartPanel spec={slideSpec(fundBand(toFund(f.ei), '₩ trillions, reserves',
              KO.series, { height: 520 }))} caption={`${KO.captions.ei} — ${f.ei.source}`} />
            <ChartPanel spec={slideSpec(timeSeries(
              central!.ei_outlay_tn.map((v, i) => ({ period: i, ei_outlay_tn: v })),
              ['ei_outlay_tn'], '₩ trillions / year', 2026, { kind: 'bar', height: 520 }))}
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
            { height: 560 }))} caption={KO.captions.composition} />
        </div>
      ) },
      { key: 'map', body: (
        <div className="slide-chart">
          <h2>{KO.sections.map}</h2>
          <ChartPanel spec={slideSpec(koreaTileMap((bundle as any).regions ?? [],
            { height: 620 }))} caption={KO.captions.map} />
        </div>
      ) },
      { key: 'sensitivity', body: (
        <div className="slide-chart">
          <h2>{KO.sections.tornado}</h2>
          <ChartPanel spec={slideSpec(koreaTornado(tornado!.targets.ei_shortfall_tn,
            (l: string) => (KOREA_GRID[l] ? leverCopy(l).label : (TORNADO_LABELS[l] ?? l)),
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
  }, [ready])

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
          <span>DRAFT · numbers final and test-pinned · strings pending the copy pass</span>
          <span className="num">{exportSlide} / {slides.length}</span>
        </div>
      </div>
    )
  }

  const scale = Math.min(1, (window.innerWidth - 48) / SLIDE_W)
  return (
    <div className="deck">
      <p className="caption deck-help">
        ← → to navigate · slide {active + 1} of {slides.length} · append ?slide=N for the
        1920×1080 export view (scripts/export_korea_slides.py writes the PNG pack)
      </p>
      <div className="slide-stage" style={{ width: SLIDE_W * scale, height: SLIDE_H * scale }}>
        <div className="slide" style={{ width: SLIDE_W, height: SLIDE_H,
                                        transform: `scale(${scale})` }}>
          {slides[active].body}
          <div className="slide-footer caption">
            <span>DRAFT · numbers final and test-pinned · strings pending the copy pass</span>
            <span className="num">{active + 1} / {slides.length}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
