// "About the model" — the button at the bottom of the rail and the dialog it opens: the
// methodology in the site's own words (copy.json korea.about, markdown), then scope and
// limits, then the run's conventions line. The US About pattern (AboutModal.tsx) with the
// Korea copy pack instead of the US strings.
import { useEffect, useRef } from 'react'
import { Markdown } from '../content/md'

export function KoreaAbout({ copy, disclosures, conventions }:
                           { copy: { button: string; title: string; body: string; scope_title: string }
                             disclosures: string[]; conventions: string }) {
  const dlg = useRef<HTMLDialogElement>(null)
  // ?about opens the dialog on load: a deep link to the methodology (and how the export
  // and screenshots reach it without a click)
  const open = () => {
    const d = dlg.current
    if (d && typeof d.showModal === 'function' && !d.open) d.showModal()
  }
  useEffect(() => {
    // not on a phone: the rail body is display:none there, and a modal whose ancestor is
    // hidden renders nothing while still making the page inert
    const railVisible = !window.matchMedia('(max-width: 900px)').matches
    if (railVisible && new URLSearchParams(location.search).has('about')) open()
  }, [])
  return (
    <div className="about-launch">
      <button type="button" className="dl" onClick={open}>{copy.button}</button>
      <dialog ref={dlg}>
        <div className="dialog-head">
          <h3>{copy.title}</h3>
          <button type="button" className="dialog-x" aria-label="Close"
                  onClick={() => dlg.current?.close()}>×</button>
        </div>
        <div className="dialog-body">
          <Markdown text={copy.body} />
          <h4>{copy.scope_title}</h4>
          <ul className="caption">
            {disclosures.map((d, i) => <li key={i}>{d}</li>)}
          </ul>
          {conventions && <p className="caption">{conventions}</p>}
        </div>
      </dialog>
    </div>
  )
}
