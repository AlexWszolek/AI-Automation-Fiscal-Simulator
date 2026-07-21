// Scenario preset + policy-response pickers, with blurbs, overlay notes, and the live
// recovers-$X readouts (all from the payload — server-computed strings and numbers).
import { OVERLAYS, PRESETS, presetMeta } from '../lib/config'
import { thousands } from '../lib/format'
import type { ScenarioConfig, ScenarioPayload } from '../lib/types'
import type { ScenarioAction } from '../state/useScenario'
import { HelpTip } from './controls'
import { ListBox } from './ListBox'

export function PresetPicker({ cfg, dispatch }: {
  cfg: ScenarioConfig
  dispatch: (a: ScenarioAction) => void
}) {
  const p = presetMeta(cfg.preset)
  return (
    <details className="group" open>
      <summary>Scenario preset</summary>
      <div className="picker">
        <ListBox
          ariaLabel="Scenario preset"
          value={cfg.preset ?? 'custom'}
          options={[{ value: 'custom', label: 'Custom' },
            ...PRESETS.map((pm) => ({ value: pm.key, label: pm.name }))]}
          onChange={(v) => dispatch({ type: 'setPreset', preset: v === 'custom' ? null : v })}
        />
        {p && <p className="caption">{p.blurb}</p>}
      </div>
    </details>
  )
}

export function OverlayPicker({ cfg, payload, dispatch }: {
  cfg: ScenarioConfig
  payload: ScenarioPayload | null
  dispatch: (a: ScenarioAction) => void
}) {
  return (
    <details className="group" open>
      <summary>Policy responses</summary>
      <div className="picker">
      {OVERLAYS.map((o) => (
        <label key={o.key} className="overlay-row">
          <input
            type="checkbox"
            checked={cfg.overlays.includes(o.key)}
            onChange={() => dispatch({ type: 'toggleOverlay', key: o.key })}
          />{' '}
          <HelpTip label={o.name} help={o.blurb} />
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
    </details>
  )
}
