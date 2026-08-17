// The Korea page (unlisted: /korea.html — a second Vite entry, zero coupling to the US
// app's codec/state). Presenter-proof by construction: no levers, the uncertainty band is
// always drawn, and the sources & disclosures panel is part of the page, not a tooltip.
// ALL user-facing text on this page is provisional until Alex's copy pass (copy.json →
// "korea"); the draft banner stays until that lands.
import { useEffect, useState } from 'react'
import copy from '../content/copy.json'
import { ChartPanel } from '../components/ChartPanel'
import { compositionBars, contrastBars, fundBand, koreaGeoMap } from '../charts/korea'
import { useKoreaData } from '../state/useKoreaData'

const KO = (copy as unknown as { korea: KoreaCopy }).korea
const T = (copy as any).korea.templates as Record<string, string>

function fmt(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? ''))
}

interface KoreaCopy {
  title: string
  intro: string
  disclosure_note: string
  sections: Record<string, string>
  captions: Record<string, string>
  series: { published: string; eroded: string; band: string }
  tooltips: Record<string, string>
  institutions: Record<string, string>
  disclosures: string[]
  metrics: Record<string, string>
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

export default function KoreaApp() {
  const { bundle, failed } = useKoreaData()
  const [topo, setTopo] = useState<object | null>(null)
  useEffect(() => {
    fetch('/data/korea-sido-topo.json').then((r) => (r.ok ? r.json() : null))
      .then(setTopo).catch(() => setTopo(null))
  }, [])
  const label = (k: string) => KO.institutions[k] ?? k

  return (
    <div className="shell korea-shell">
      <main className="content korea-content">
        <div className="col-wide">
          <p className="panel caption draft-banner">{T.draft_banner}</p>
          <h1>{KO.title}</h1>
          <p>{KO.intro}</p>
          <p className="panel caption">{KO.disclosure_note}</p>
        </div>

        {failed && (
          <p className="panel caption col-wide warning">{T.bundle_failed}</p>
        )}

        {bundle && (
          <>
            <div className="col-wide">
              <div className="metric-row heroes korea-heroes">
                <Metric
                  label={KO.metrics.nps}
                  value={fmt(T.p_nps_value, { v: yearsFmt(bundle.headlines.nps.given_back_central),
                                              n: bundle.headlines.nps.bought_years })}
                  ground={fmt(T.p_nps_ground, { lo: yearsFmt(bundle.headlines.nps.given_back_lo),
                    hi: yearsFmt(bundle.headlines.nps.given_back_hi),
                    pre: bundle.headlines.nps.pre_reform_depletion,
                    pub: bundle.headlines.nps.published_depletion })}
                />
                <Metric
                  label={KO.metrics.nhi}
                  value={fmt(T.nhi_value, { v: yearsFmt(bundle.headlines.nhi.years_forward_central) })}
                  ground={fmt(T.p_nhi_ground, { lo: yearsFmt(bundle.headlines.nhi.years_forward_lo),
                    hi: yearsFmt(bundle.headlines.nhi.years_forward_hi),
                    pub: bundle.headlines.nhi.published_depletion })}
                />
                <Metric
                  label={KO.metrics.ei}
                  value={fmt(T.ei_value, { v: bundle.headlines.ei.shortfall_central_tn.toFixed(1) })}
                  ground={fmt(T.p_ei_ground, { lo: bundle.headlines.ei.shortfall_lo_tn.toFixed(1),
                    hi: bundle.headlines.ei.shortfall_hi_tn.toFixed(1),
                    plan: bundle.headlines.ei.planned_2029_tn.toFixed(1) })}
                />
              </div>
            </div>

            <div className="col-wide chart-grid korea-grid">
              <ChartPanel
                title={KO.sections.nps}
                spec={fundBand(bundle.funds.nps, '₩ trillions, reserves', KO.series, { tips: KO.tooltips })}
                caption={`${KO.captions.nps} — ${bundle.funds.nps.source}`}
              />
              <ChartPanel
                title={KO.sections.nhi}
                spec={fundBand(bundle.funds.nhi, '₩ trillions, reserves', KO.series, { tips: KO.tooltips })}
                caption={`${KO.captions.nhi} — ${bundle.funds.nhi.source}`}
              />
              <ChartPanel
                title={KO.sections.ei}
                spec={fundBand(bundle.funds.ei, '₩ trillions, reserves', KO.series, { height: 260, tips: KO.tooltips })}
                caption={`${KO.captions.ei} — ${bundle.funds.ei.source}`}
              />
              <ChartPanel
                title={KO.sections.composition}
                spec={compositionBars(bundle.composition.central_2035, label, { tips: KO.tooltips })}
                caption={KO.captions.composition}
              />
              {bundle.regions && topo && (
                <ChartPanel
                  title={KO.sections.map}
                  spec={koreaGeoMap(bundle.regions, topo, { tips: KO.tooltips })}
                  caption={KO.captions.map}
                />
              )}
              <ChartPanel
                title={KO.sections.contrast}
                spec={contrastBars(
                  bundle.composition.white_collar_only,
                  bundle.composition.elementary_only,
                  { a: KO.metrics.contrast_a, b: KO.metrics.contrast_b },
                  label,
                  { tips: KO.tooltips },
                )}
                caption={KO.captions.contrast}
              />
            </div>

            <div className="col-wide panel korea-sources">
              <h2>{KO.sections.sources}</h2>
              <ul className="caption">
                {bundle.sources.map((s) => (
                  <li key={s.name}><strong>{s.name}.</strong> {s.cite}</li>
                ))}
              </ul>
              <h2>{KO.sections.disclosures}</h2>
              <ul className="caption">
                {KO.disclosures.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
              <p className="caption">
                {fmt(T.model_config, { chain: bundle.config.chain,
                  central: bundle.config.central, band: bundle.config.band,
                  adoption: bundle.config.adoption })}
              </p>
            </div>
          </>
        )}

        {!bundle && !failed && <p className="caption col-wide">Loading…</p>}
      </main>
    </div>
  )
}
