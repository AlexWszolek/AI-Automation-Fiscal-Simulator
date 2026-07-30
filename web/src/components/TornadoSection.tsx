// Always-on sensitivity tornado: instant for presets (committed entries), auto-recompute with
// debounce + progress for modified settings — the Streamlit fragment's behavior, served by the
// compute service.
import { tornado } from '../charts/tornado'
import { thousands } from '../lib/format'
import type { ScenarioConfig, TornadoEntry } from '../lib/types'
import { useCompact } from '../lib/useCompact'
import { useTornado } from '../state/useTornado'
import { ChartPanel } from './ChartPanel'

function Caption({ e }: { e: TornadoEntry }) {
  return (
    <>
      Each bar is a <em>Spearman rank correlation</em>: across{' '}
      <span className="num">{e.n}</span> model runs that vary live assumptions ±15% around
      the settings, how consistently does raising that assumption move the final-year
      deficit? <span className="num">±1</span> means perfectly correlated, near{' '}
      <span className="num">0</span> means little independent influence. Across those runs
      the final-year deficit increase stays between{' '}
      <span className="num">${thousands(e.p10)}B</span> and{' '}
      <span className="num">${thousands(e.p90)}B</span> (P10–P90). This band measures
      robustness to mis-calibrated assumptions within this scenario.
    </>
  )
}

export function TornadoSection({ cfg }: { cfg: ScenarioConfig }) {
  const t = useTornado(cfg)
  const compact = useCompact()

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
          Sensitivity recompute needs the compute service, which is not reachable right now;
          showing last available analysis.
        </p>
      )}
      {t.entry ? (
        <figure className="chart-panel">
          <ChartPanel spec={tornado(t.entry, 12, t.stale, compact)} />
          <figcaption className="caption"><Caption e={t.entry} /></figcaption>
        </figure>
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
