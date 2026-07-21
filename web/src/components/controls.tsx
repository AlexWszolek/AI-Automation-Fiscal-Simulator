// The input primitives + the receding help affordance. No component library — plain elements
// styled by app.css; every control shows its current value in mono tabular-nums.
import { useId, useState } from 'react'
import type { GridSpecNum } from '../lib/config'
import { trueMinus } from '../lib/format'
import { ListBox } from './ListBox'

/** Receding help: a dotted-underline label that reveals the app's help text on hover/focus.
    No ⓘ icons (approved deviation). */
export function HelpTip({ label, help }: { label: string; help?: string | null }) {
  const [open, setOpen] = useState(false)
  if (!help) return <span className="lever-label">{label}</span>
  return (
    <span
      className="lever-label has-help"
      tabIndex={0}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {label}
      {open && <span className="help-pop caption">{help}</span>}
    </span>
  )
}

function fmtValue(v: number, spec: GridSpecNum): string {
  const digits = spec.type === 'int' ? 0 : Math.max(0, -Math.floor(Math.log10(spec.step)))
  return trueMinus(v.toFixed(digits))
}

export function SliderControl({ label, help, spec, value, min, max, disabled, onChange }: {
  label: string
  help?: string | null
  spec: GridSpecNum
  value: number
  min?: number            // runtime clamp overrides (price max, robot-tax bound)
  max?: number
  disabled?: boolean
  onChange: (v: number) => void
}) {
  const id = useId()
  const lo = min ?? spec.lo
  const hi = max ?? spec.hi
  return (
    <div className={`lever${disabled ? ' disabled' : ''}`}>
      <div className="lever-head">
        <HelpTip label={label} help={help} />
        <label htmlFor={id} className="num lever-value">{fmtValue(value, spec)}</label>
      </div>
      <input
        id={id}
        type="range"
        min={lo}
        max={hi}
        step={spec.step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(spec.type === 'int' ? Math.round(+e.target.value) : +e.target.value)}
      />
    </div>
  )
}

export function SelectControl({ label, help, values, value, display, onChange }: {
  label: string
  help?: string | null
  values: string[]
  value: string
  display?: Record<string, string>
  onChange: (v: string) => void
}) {
  return (
    <div className="lever">
      <div className="lever-head">
        <HelpTip label={label} help={help} />
      </div>
      <ListBox
        ariaLabel={label}
        value={value}
        options={values.map((v) => ({ value: v, label: display?.[v] ?? v }))}
        onChange={onChange}
      />
    </div>
  )
}

export function CheckboxControl({ label, help, value, onChange }: {
  label: string
  help?: string | null
  value: boolean
  onChange: (v: boolean) => void
}) {
  const id = useId()
  return (
    <div className="lever lever-checkbox">
      <input id={id} type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)} />
      <label htmlFor={id}>
        <HelpTip label={label} help={help} />
      </label>
    </div>
  )
}
