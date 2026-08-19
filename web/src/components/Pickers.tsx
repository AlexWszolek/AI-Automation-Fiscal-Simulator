// Scenario preset + policy-response pickers, with blurbs and overlay notes. (The live
// recovers-$X readouts were removed in copy round 2; the payload still carries the data.)
import { OVERLAYS, PRESETS, presetMeta } from '../lib/config'
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
  // rendered INSIDE the Government policy lever group — the checkboxes are policy
  // responses like every dial around them, not a privileged section of their own
  return (
    <div className="picker overlay-rows">
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
        <p key={n} className="caption">{n}</p>
      ))}
    </div>
  )
}
