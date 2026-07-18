// Always-on sensitivity tornado: instant for presets (committed entries), auto-recompute with
// debounce + progress for modified settings — the Streamlit fragment's behavior, served by the
// compute service.
import { tornado } from '../charts/tornado'
import { thousands } from '../lib/format'
import type { ScenarioConfig, TornadoEntry } from '../lib/types'
import { useTornado } from '../state/useTornado'
import { ChartPanel } from './ChartPanel'

function caption(e: TornadoEntry): string {
  return `Each bar shows how strongly one assumption drives the final-year deficit, across ${e.n} model runs that jitter every live assumption ±15% around your settings; red means raising it worsens the deficit, blue means it improves it. Across those runs the final-year deficit increase stays between $${thousands(e.p10)}B and $${thousands(e.p90)}B (P10-P90). That band measures robustness to mis-calibrated assumptions within this scenario — the honest uncertainty about the future is the spread across the scenario presets themselves.`
}

export function TornadoSection({ cfg }: { cfg: ScenarioConfig }) {
  const t = useTornado(cfg)

  return (
    <section className="col-wide">
      <h2>Which assumptions drive this number?</h2>
      {t.stale && !t.unavailable && (
        <p className="caption">
          <strong>Settings changed — updating the sensitivity analysis in a few seconds…</strong>{' '}
          (showing the previous configuration meanwhile)
        </p>
      )}
      {t.progress && (
        <p className="caption num">
          stress-testing your settings… {t.progress.done}/{t.progress.total} runs
          <progress value={t.progress.done} max={t.progress.total} style={{ width: '100%' }} />
        </p>
      )}
      {t.unavailable && (
        <p className="caption">
          Sensitivity recompute needs the compute service, which is not reachable right now —
          showing the last available analysis. Preset sensitivities work offline.
        </p>
      )}
      {t.entry ? (
        <ChartPanel spec={tornado(t.entry, 12, t.stale)} caption={caption(t.entry)} />
      ) : (
        !t.progress && (
          <p className="caption">
            Sensitivity analysis starts a few seconds after you stop moving sliders…
          </p>
        )
      )}
    </section>
  )
}
