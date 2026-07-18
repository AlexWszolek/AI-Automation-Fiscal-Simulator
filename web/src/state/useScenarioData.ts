// Data for the current config: pristine configs fetch a committed static bundle by slug
// (instant, works with the API down); lever-modified configs go to POST /api/run with a
// 300ms debounce (Phase 3 — until the API lands, custom configs surface `apiDown`).
// Always keeps the last good payload on screen while the next one loads.
import { useEffect, useRef, useState } from 'react'
import { isPristine, slugFor } from '../lib/config'
import type { ScenarioConfig, ScenarioPayload } from '../lib/types'

export interface ScenarioData {
  payload: ScenarioPayload | null
  loading: boolean
  apiDown: boolean
}

const bundleCache = new Map<string, ScenarioPayload>()

export function useScenarioData(cfg: ScenarioConfig): ScenarioData {
  const [payload, setPayload] = useState<ScenarioPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [apiDown, setApiDown] = useState(false)
  const seq = useRef(0)

  useEffect(() => {
    const mySeq = ++seq.current
    const cancelled = () => seq.current !== mySeq
    setLoading(true)

    async function fetchStatic() {
      const slug = slugFor(cfg)
      const cached = bundleCache.get(slug)
      if (cached) return cached
      const r = await fetch(`/data/scenarios/${slug}.json`)
      if (!r.ok) throw new Error(`bundle ${slug}: ${r.status}`)
      const p = (await r.json()) as ScenarioPayload
      bundleCache.set(slug, p)
      return p
    }

    async function fetchLive() {
      const r = await fetch('/api/run', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(cfg),
      })
      if (!r.ok) throw new Error(`api: ${r.status}`)
      return (await r.json()) as ScenarioPayload
    }

    const run = async () => {
      try {
        const p = await (isPristine(cfg) ? fetchStatic() : fetchLive())
        if (!cancelled()) {
          setPayload(p)
          setApiDown(false)
          setLoading(false)
        }
      } catch {
        if (!cancelled()) {
          setApiDown(!isPristine(cfg))
          setLoading(false)
        }
      }
    }

    // debounce only the live path — static bundles are instant and cached
    if (isPristine(cfg)) {
      void run()
      return
    }
    const t = setTimeout(run, 300)
    return () => clearTimeout(t)
  }, [cfg])

  return { payload, loading, apiDown }
}
