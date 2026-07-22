// Mounts a vega-lite spec and shows the app's caption under it (the show_chart pattern).
// The vega runtime is dynamically imported (its ~380KB chunk stays off the first paint), and
// `lazy` charts (the map with its topojson) mount only when scrolled near the viewport.
// A ResizeObserver re-embeds when the container's width actually changes (width:'container'
// only measures at embed time) — phone rotation, window resizes, drawer settling.
import { useEffect, useRef, useState } from 'react'
import type { VisualizationSpec } from 'vega-embed'
import type { Result } from 'vega-embed'

export function ChartPanel({ spec, caption, title, lazy }: {
  spec: VisualizationSpec
  caption?: string
  title?: string
  lazy?: boolean
}) {
  const el = useRef<HTMLDivElement>(null)
  const [near, setNear] = useState(!lazy)
  const [fitWidth, setFitWidth] = useState(0)

  useEffect(() => {
    if (!lazy || near || !el.current) return
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        setNear(true)
        io.disconnect()
      }
    }, { rootMargin: '400px' })
    io.observe(el.current)
    return () => io.disconnect()
  }, [lazy, near])

  useEffect(() => {
    if (!el.current) return
    let timer: ReturnType<typeof setTimeout> | undefined
    const ro = new ResizeObserver((entries) => {
      const w = Math.round(entries[0].contentRect.width)
      clearTimeout(timer)
      timer = setTimeout(() => {
        setFitWidth((prev) => (Math.abs(w - prev) > 8 ? w : prev))
      }, 150)
    })
    ro.observe(el.current)
    return () => {
      clearTimeout(timer)
      ro.disconnect()
    }
  }, [])

  useEffect(() => {
    if (!near) return
    let result: Result | undefined
    let gone = false
    if (el.current) {
      void import('../charts/vega').then(({ mount }) => {
        if (gone || !el.current) return
        return mount(el.current, spec).then((r) => {
          if (gone) r.finalize()
          else result = r
        })
      })
    }
    return () => {
      gone = true
      result?.finalize()
    }
  }, [spec, near, fitWidth])

  return (
    <figure className="chart-panel">
      {title && <h2>{title}</h2>}
      <div ref={el} style={{ width: '100%', minHeight: lazy && !near ? 420 : undefined }} />
      {caption && <figcaption className="caption">{caption}</figcaption>}
    </figure>
  )
}
