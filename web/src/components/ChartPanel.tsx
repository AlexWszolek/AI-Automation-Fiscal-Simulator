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

  // Slider updates change only the DATA of a structurally identical spec — swap the dataset
  // on the live vega view (fast: no parse/compile/re-mount) and fall back to a full re-embed
  // whenever the structure differs (series set, year count, compact variant) or the swap throws.
  const resultRef = useRef<Result | null>(null)
  const structKeyRef = useRef('')

  useEffect(() => {
    if (!near) return
    let gone = false
    const values = (spec as { data?: { values?: unknown[] } }).data?.values
    const structKey = JSON.stringify({ ...(spec as object), data: null }) + `|${fitWidth}`
    void import('../charts/vega').then(async ({ mount }) => {
      if (gone || !el.current) return
      if (resultRef.current && structKeyRef.current === structKey && values) {
        try {
          const t0 = performance.now()
          const view = resultRef.current.view
          view.data('source_0', values)
          await view.resize().runAsync()
          if (import.meta.env.DEV) console.debug(`[chart] data-swap ${(performance.now() - t0).toFixed(0)}ms`)
          return
        } catch { /* structure drifted after all — re-embed below */ }
      }
      resultRef.current?.finalize()
      resultRef.current = null
      const t0 = performance.now()
      const r = await mount(el.current, spec)
      if (gone) {
        r.finalize()
        return
      }
      resultRef.current = r
      structKeyRef.current = structKey
      if (import.meta.env.DEV) console.debug(`[chart] embed ${(performance.now() - t0).toFixed(0)}ms`)
    })
    return () => {
      gone = true
    }
  }, [spec, near, fitWidth])

  useEffect(() => () => {
    resultRef.current?.finalize()
    resultRef.current = null
  }, [])

  return (
    <figure className="chart-panel">
      {title && <h2>{title}</h2>}
      <div ref={el} style={{ width: '100%', minHeight: lazy && !near ? 420 : undefined }} />
      {caption && <figcaption className="caption">{caption}</figcaption>}
    </figure>
  )
}
