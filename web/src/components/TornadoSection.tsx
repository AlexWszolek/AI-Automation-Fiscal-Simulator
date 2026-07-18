// Always-on sensitivity tornado. Pristine configs render the precomputed entry instantly from
// the committed tornado.json; lever-modified configs get the API job (Phase 3 — until then a
// quiet placeholder names the compute service).
import { useEffect, useState } from 'react'
import { tornado } from '../charts/tornado'
import { isPristine, slugFor } from '../lib/config'
import { thousands } from '../lib/format'
import type { ScenarioConfig, TornadoEntry } from '../lib/types'
import { ChartPanel } from './ChartPanel'

let tornadoIndex: Record<string, TornadoEntry> | null = null

function caption(e: TornadoEntry): string {
  return `Each bar shows how strongly one assumption drives the final-year deficit, across ${e.n} model runs that jitter every live assumption ±15% around your settings; red means raising it worsens the deficit, blue means it improves it. Across those runs the final-year deficit increase stays between $${thousands(e.p10)}B and $${thousands(e.p90)}B (P10-P90). That band measures robustness to mis-calibrated assumptions within this scenario — the honest uncertainty about the future is the spread across the scenario presets themselves.`
}

export function TornadoSection({ cfg }: { cfg: ScenarioConfig }) {
  const [entry, setEntry] = useState<TornadoEntry | null>(null)

  useEffect(() => {
    let gone = false
    async function load() {
      if (!isPristine(cfg)) {
        setEntry(null)
        return
      }
      if (!tornadoIndex) {
        const r = await fetch('/data/tornado.json')
        tornadoIndex = (await r.json()) as Record<string, TornadoEntry>
      }
      if (!gone) setEntry(tornadoIndex[slugFor(cfg)] ?? null)
    }
    void load()
    return () => {
      gone = true
    }
  }, [cfg])

  return (
    <section className="col-wide">
      <h2>Which assumptions drive this number?</h2>
      {entry ? (
        <ChartPanel spec={tornado(entry)} caption={caption(entry)} />
      ) : (
        <p className="caption">
          Sensitivity analysis for modified settings runs on the compute service — it starts a
          few seconds after you stop moving sliders.
        </p>
      )}
    </section>
  )
}
