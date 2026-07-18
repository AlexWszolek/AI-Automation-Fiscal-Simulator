// The one piece of app state: {preset, overlays, levers}. Levers hold ONLY diffs from the
// preset's defaults (the URL-codec representation); switching presets clears them — the
// Streamlit value-swap semantics.
import { useReducer } from 'react'
import { defaultsFor } from '../lib/config'
import type { LeverValue, ScenarioConfig } from '../lib/types'

export type ScenarioAction =
  | { type: 'setPreset'; preset: string | null }
  | { type: 'toggleOverlay'; key: string }
  | { type: 'setLever'; key: string; value: LeverValue }
  | { type: 'load'; config: ScenarioConfig }

function valuesClose(a: LeverValue, b: LeverValue, step: number): boolean {
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) < step / 2.001
  return a === b
}

export function reduce(cfg: ScenarioConfig, action: ScenarioAction): ScenarioConfig {
  switch (action.type) {
    case 'setPreset':
      return { preset: action.preset, overlays: cfg.overlays, levers: {} }
    case 'toggleOverlay': {
      const had = cfg.overlays.includes(action.key)
      let overlays = had
        ? cfg.overlays.filter((k) => k !== action.key)
        : [...cfg.overlays, action.key]
      // both robot taxes set the same lever — adding one drops the other (the app's rule)
      if (!had && action.key === 'cw-robot-tax') overlays = overlays.filter((k) => k !== 'grt-robot-tax')
      if (!had && action.key === 'grt-robot-tax') overlays = overlays.filter((k) => k !== 'cw-robot-tax')
      return { ...cfg, overlays }
    }
    case 'setLever': {
      const d = defaultsFor(cfg.preset)
      const levers = { ...cfg.levers }
      const dv = d[action.key]
      // a lever back on its default is not a diff — drop it so the config stays pristine-able
      if (typeof dv === 'number' && typeof action.value === 'number'
          && valuesClose(action.value, dv, 1e-9)) delete levers[action.key]
      else if (dv === action.value) delete levers[action.key]
      else levers[action.key] = action.value
      return { ...cfg, levers }
    }
    case 'load':
      return action.config
  }
}

export const INITIAL: ScenarioConfig = { preset: 'acemoglu-modest', overlays: [], levers: {} }

export function useScenario(initial: ScenarioConfig = INITIAL) {
  return useReducer(reduce, initial)
}
