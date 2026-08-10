// The Korea page (unlisted: /korea.html — a second Vite entry, zero coupling to the US
// app's codec/state). Presenter-proof by construction: no levers, the uncertainty band is
// always drawn, and the sources & disclosures panel is part of the page, not a tooltip.
// ALL user-facing text on this page is provisional until Alex's copy pass (copy.json →
// "korea"); the draft banner stays until that lands.
import copy from '../content/copy.json'
import { ChartPanel } from '../components/ChartPanel'
import { compositionBars, contrastBars, fundBand } from '../charts/korea'
import { useKoreaData } from '../state/useKoreaData'

const KO = (copy as unknown as { korea: KoreaCopy }).korea

interface KoreaCopy {
  title: string
  intro: string
  ceiling_note: string
  sections: Record<string, string>
  captions: Record<string, string>
  series: { published: string; eroded: string; band: string }
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
  const label = (k: string) => KO.institutions[k] ?? k

  return (
    <div className="shell korea-shell">
      <main className="content korea-content">
        <div className="col-wide">
          <p className="panel caption draft-banner">
            DRAFT — every string on this page is provisional until the copy pass
            (content/copy.json → &quot;korea&quot;). Numbers are final and test-pinned.
          </p>
          <h1>{KO.title}</h1>
          <p>{KO.intro}</p>
          <p className="panel caption">{KO.ceiling_note}</p>
        </div>

        {failed && (
          <p className="panel caption col-wide warning">
            The Korea data bundle (/data/korea.json) could not be loaded. If this is a fresh
            deployment, run scripts/gen_korea_bundle.py and redeploy.
          </p>
        )}

        {bundle && (
          <>
            <div className="col-wide">
              <div className="metric-row heroes korea-heroes">
                <Metric
                  label={KO.metrics.nps}
                  value={`${yearsFmt(bundle.headlines.nps.given_back_central)} of ${bundle.headlines.nps.bought_years} yrs`}
                  ground={`band ${yearsFmt(bundle.headlines.nps.given_back_lo)}–${yearsFmt(bundle.headlines.nps.given_back_hi)} · reform moved depletion ${bundle.headlines.nps.pre_reform_depletion} → ${bundle.headlines.nps.published_depletion}`}
                />
                <Metric
                  label={KO.metrics.nhi}
                  value={`${yearsFmt(bundle.headlines.nhi.years_forward_central)} yrs earlier`}
                  ground={`band ${yearsFmt(bundle.headlines.nhi.years_forward_lo)}–${yearsFmt(bundle.headlines.nhi.years_forward_hi)} · published depletion ${bundle.headlines.nhi.published_depletion}`}
                />
                <Metric
                  label={KO.metrics.ei}
                  value={`₩${bundle.headlines.ei.shortfall_central_tn.toFixed(1)}tn short`}
                  ground={`band ₩${bundle.headlines.ei.shortfall_lo_tn.toFixed(1)}–${bundle.headlines.ei.shortfall_hi_tn.toFixed(1)}tn vs the planned ₩${bundle.headlines.ei.planned_2029_tn.toFixed(1)}tn rebuild by 2029`}
                />
              </div>
            </div>

            <div className="col-wide chart-grid korea-grid">
              <ChartPanel
                title={KO.sections.nps}
                spec={fundBand(bundle.funds.nps, '₩ trillions, reserves', KO.series)}
                caption={`${KO.captions.nps} — ${bundle.funds.nps.source}`}
              />
              <ChartPanel
                title={KO.sections.nhi}
                spec={fundBand(bundle.funds.nhi, '₩ trillions, reserves', KO.series)}
                caption={`${KO.captions.nhi} — ${bundle.funds.nhi.source}`}
              />
              <ChartPanel
                title={KO.sections.ei}
                spec={fundBand(bundle.funds.ei, '₩ trillions, reserves', KO.series, { height: 260 })}
                caption={`${KO.captions.ei} — ${bundle.funds.ei.source}`}
              />
              <ChartPanel
                title={KO.sections.composition}
                spec={compositionBars(bundle.composition.central_2035, label)}
                caption={KO.captions.composition}
              />
              <ChartPanel
                title={KO.sections.contrast}
                spec={contrastBars(
                  bundle.composition.white_collar_only,
                  bundle.composition.elementary_only,
                  { a: KO.metrics.contrast_a, b: KO.metrics.contrast_b },
                  label,
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
                Model config: {bundle.config.chain}. Central = {bundle.config.central}.
                Band = {bundle.config.band}. Adoption: {bundle.config.adoption}.
              </p>
            </div>
          </>
        )}

        {!bundle && !failed && <p className="caption col-wide">Loading…</p>}
      </main>
    </div>
  )
}
