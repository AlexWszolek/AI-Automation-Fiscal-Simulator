// The lever rail: 6 collapsible groups from the extracted copy (order + membership + labels +
// help are the app's, byte-for-byte). Clamp rules mirror app/streamlit_app.py: the price share
// is capped at 1−retained, and the robot tax at its retained-profit bound (disabled under 1%).
import copy from '../content/copy.json'
import { GRID, ataxBound, effectiveLevers, priceMax, survivorRemainder } from '../lib/config'
import type { GridSpecEnum, GridSpecNum } from '../lib/config'
import type { LeverValue, ScenarioConfig } from '../lib/types'
import type { ScenarioAction } from '../state/useScenario'
import { CheckboxControl, SelectControl, SliderControl } from './controls'

interface LeverCopy { label: string; help: string | null; widget: string }
const LEVER_COPY = copy.levers as Record<string, LeverCopy>
const GROUPS = copy.groups as { title: string; expanded: boolean; keys: string[] }[]

export function LeverRow({ k, values, dispatch }: {
  k: string
  values: Record<string, LeverValue>
  dispatch: (a: ScenarioAction) => void
}) {
  const spec = GRID[k]
  const c = LEVER_COPY[k]
  const set = (value: LeverValue) => dispatch({ type: 'setLever', key: k, value })

  if (spec.type === 'bool')
    return <CheckboxControl label={c.label} help={c.help} value={Boolean(values[k])} onChange={set} />
  if (spec.type === 'enum') {
    const display = k === 'state_resp'
      ? { mix: 'Mix of both', raise_rates: 'Raise taxes', cut_spending: 'Cut spending' }
      : undefined
    return (
      <SelectControl label={c.label} help={c.help} values={(spec as GridSpecEnum).values}
                     value={String(values[k])} display={display} onChange={set} />
    )
  }

  const num = spec as GridSpecNum
  const retained = Number(values.retained)
  if (k === 'price') {
    const max = priceMax(retained)
    if (max <= 0) return null                        // retained = 100% → no room (the app hides it)
    return (
      <SliderControl label={c.label} help={c.help} spec={num} max={max}
                     value={Math.min(Number(values[k]), max)} onChange={set} />
    )
  }
  if (k === 'atax') {
    const bound = ataxBound(retained, Number(values.auto_cost))
    if (bound < 0.01)
      return (
        <p className="caption">
          Automation tax: 0% — no retained profit left to pay it (retained × (1 − auto cost) ≈ 0).
        </p>
      )
    return (
      <SliderControl label={c.label} help={c.help} spec={num} max={bound}
                     value={Math.min(Number(values[k]), bound)} onChange={set} />
    )
  }
  if (k === 'ceiling')
    return (
      <SliderControl label={c.label} help={c.help} spec={num} value={Number(values[k])}
                     disabled={Boolean(values.unbounded)} onChange={set} />
    )
  return <SliderControl label={c.label} help={c.help} spec={num} value={Number(values[k])} onChange={set} />
}

/** The three state-response controls render inside the states section, not the rail. */
const STATE_KEYS = new Set(['state_resp', 'state_cut', 'rate_cap'])

export function LeverPanel({ cfg, dispatch }: {
  cfg: ScenarioConfig
  dispatch: (a: ScenarioAction) => void
}) {
  const values = effectiveLevers(cfg)
  return (
    <>
      {GROUPS.map((g) => (
        <details key={g.title} className="group" open={g.expanded}>
          <summary>{g.title}</summary>
          {g.keys.filter((k) => !STATE_KEYS.has(k)).map((k) => (
            <LeverRow key={k} k={k} values={values} dispatch={dispatch} />
          ))}
          {g.title === 'Firms & compute' && (
            <p className="caption">
              → Raises for remaining staff:{' '}
              {Math.round(survivorRemainder(Number(values.retained), Math.min(Number(values.price), Math.max(priceMax(Number(values.retained)), 0))) * 100)}
              % (the remainder)
            </p>
          )}
        </details>
      ))}
    </>
  )
}
