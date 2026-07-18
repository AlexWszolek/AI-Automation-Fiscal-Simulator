// Mounts a vega-lite spec and shows the app's caption under it (the show_chart pattern).
import { useEffect, useRef } from 'react'
import type { VisualizationSpec } from 'vega-embed'
import type { Result } from 'vega-embed'
import { mount } from '../charts/vega'

export function ChartPanel({ spec, caption, title }: {
  spec: VisualizationSpec
  caption?: string
  title?: string
}) {
  const el = useRef<HTMLDivElement>(null)
  useEffect(() => {
    let result: Result | undefined
    let gone = false
    if (el.current) {
      void mount(el.current, spec).then((r) => {
        if (gone) r.finalize()
        else result = r
      })
    }
    return () => {
      gone = true
      result?.finalize()
    }
  }, [spec])
  return (
    <figure className="chart-panel">
      {title && <h2>{title}</h2>}
      <div ref={el} style={{ width: '100%' }} />
      {caption && <figcaption className="caption">{caption}</figcaption>}
    </figure>
  )
}
