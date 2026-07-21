// A fully site-styled select: the native <select>'s OPEN menu is the OS's and cannot be
// styled, so this is the accessible combobox/listbox pattern — button + popover list with
// full keyboard support (arrows, Home/End, Enter/Space, Escape) and click-outside close.
import { useEffect, useId, useRef, useState } from 'react'

export interface ListOption { value: string; label: string }

export function ListBox({ value, options, onChange, ariaLabel }: {
  value: string
  options: ListOption[]
  onChange: (v: string) => void
  ariaLabel: string
}) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(() => Math.max(0, options.findIndex((o) => o.value === value)))
  const root = useRef<HTMLDivElement>(null)
  const listId = useId()
  const current = options.find((o) => o.value === value)

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  const openAt = (idx: number) => {
    setActive(Math.max(0, idx))
    setOpen(true)
  }
  const commit = (idx: number) => {
    const o = options[idx]
    if (o) onChange(o.value)
    setOpen(false)
  }

  const onKey = (e: React.KeyboardEvent) => {
    const idx = options.findIndex((o) => o.value === value)
    if (!open) {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) {
        e.preventDefault()
        openAt(idx)
      }
      return
    }
    switch (e.key) {
      case 'ArrowDown': e.preventDefault(); setActive((a) => Math.min(options.length - 1, a + 1)); break
      case 'ArrowUp': e.preventDefault(); setActive((a) => Math.max(0, a - 1)); break
      case 'Home': e.preventDefault(); setActive(0); break
      case 'End': e.preventDefault(); setActive(options.length - 1); break
      case 'Enter': case ' ': e.preventDefault(); commit(active); break
      case 'Escape': e.preventDefault(); setOpen(false); break
    }
  }

  return (
    <div className="listbox" ref={root} onKeyDown={onKey}>
      <button
        type="button"
        className="listbox-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        aria-controls={open ? listId : undefined}
        onClick={() => (open ? setOpen(false) : openAt(options.findIndex((o) => o.value === value)))}
      >
        <span>{current?.label ?? value}</span>
        <span className="listbox-chevron" aria-hidden>▾</span>
      </button>
      {open && (
        <ul className="listbox-pop" role="listbox" id={listId} aria-label={ariaLabel}>
          {options.map((o, i) => (
            <li
              key={o.value}
              role="option"
              aria-selected={o.value === value}
              className={`listbox-opt${i === active ? ' active' : ''}${o.value === value ? ' selected' : ''}`}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => commit(i)}
            >
              {o.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
