// Scenario preset + policy-response pickers, with blurbs, overlay notes, and the live
// recovers-$X readouts (all from the payload — server-computed strings and numbers).
import { OVERLAYS, PRESETS, presetMeta } from '../lib/config'
import { thousands } from '../lib/format'
import type { ScenarioConfig, ScenarioPayload } from '../lib/types'
import type { ScenarioAction } from '../state/useScenario'

export function PresetPicker({ cfg, dispatch }: {
  cfg: ScenarioConfig
  dispatch: (a: ScenarioAction) => void
}) {
  const p = presetMeta(cfg.preset)
  return (
    <div className="picker">
      <h3>Scenario preset</h3>
      <select
        value={cfg.preset ?? 'custom'}
        onChange={(e) => dispatch({ type: 'setPreset', preset: e.target.value === 'custom' ? null : e.target.value })}
      >
        <option value="custom">Custom</option>
        {PRESETS.map((pm) => (
          <option key={pm.key} value={pm.key}>{pm.name}</option>
        ))}
      </select>
      {p && <p className="caption">{p.blurb}</p>}
    </div>
  )
}

export function OverlayPicker({ cfg, payload, dispatch }: {
  cfg: ScenarioConfig
  payload: ScenarioPayload | null
  dispatch: (a: ScenarioAction) => void
}) {
  return (
    <div className="picker">
      <h3>Policy responses</h3>
      {OVERLAYS.map((o) => (
        <label key={o.key} className="overlay-row">
          <input
            type="checkbox"
            checked={cfg.overlays.includes(o.key)}
            onChange={() => dispatch({ type: 'toggleOverlay', key: o.key })}
          />{' '}
          {o.name}
        </label>
      ))}
      {payload?.config.overlay_notes.map((n) => (
        <p key={n} className="caption">🏛 {n}</p>
      ))}
      {payload?.overlay_readouts.map((r) => (
        <p key={r.key} className="caption">
          → {r.name}{' '}
          {r.no_gap
            ? ': the base scenario shows no final-year deficit deterioration to recover against'
            : `recovers $${thousands(r.recovered_B)}B/yr of the $${thousands(r.gap_B)}B/yr final-year gap (${thousands(r.pct ?? 0)}%)`}
        </p>
      ))}
      {payload?.overlay_readouts_combined && (
        <p className="caption">
          → All selected together recover ${thousands(payload.overlay_readouts_combined.recovered_B)}B/yr
          ({thousands(payload.overlay_readouts_combined.pct)}% of the gap)
        </p>
      )}
    </div>
  )
}
