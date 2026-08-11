// Payload for the current Korea config: pristine → the committed static bundle (instant,
// API-down-proof); modified levers → POST /api/korea/run, debounced with in-flight
// coalescing (the US hook's discipline: at most one live request on the wire; stale ticks
// exit at the cancellation check). Last good payload stays on screen while the next loads.
import { useEffect, useRef, useState } from 'react'
import { deviations, isPristine, type KoreaConfig } from './config'

export interface KoreaFundJson {
  years: number[]
  published: number[]
  eroded: number[]
  eroded_lo: number[]
  eroded_hi: number[]
  published_depletion: number | null
  years_pulled_forward: number | null
  eroded_date: number | null
  source: string
}
export interface KoreaScenarioPayload {
  config: {
    country: string
    preset: string
    levers: Record<string, number>
    start_year: number
    display_periods: number
    horizon: number
    modified_fields: string[]
    overlays: string[]
    conventions: string
  }
  rows: Record<string, number>[]
  final: {
    jobs_lost_M: number
    employment_drop_pct: number
    fed_deficit_B: number
    W_survivor: number
    nhi_years_forward: number
    nps_given_back: number
    ei_shortfall_tn: number
  }
  funds: { nhi: KoreaFundJson; nps: KoreaFundJson; ei: KoreaFundJson }
  composition_2035: Record<string, number>
  ei_outlay_tn: number[]
  overlay_readouts: {
    key: string
    revenue_final_tn?: number
    deficit_widening_final_tn?: number
    coverage_pct?: number | null
    profit_share?: number
    flow_final_tn?: number
    given_back_base?: number
    given_back_with_mandate?: number
    years_bought_back?: number
    eroded_date_with_mandate?: number | null
    provenance: string
  }[]
  band_note: string
}

export interface KoreaScenarioData {
  payload: KoreaScenarioPayload | null
  loading: boolean
  apiDown: boolean
  failed: boolean
}

const bundleCache = new Map<string, KoreaScenarioPayload>()
const DEBOUNCE_MS = 150
let liveQueue: Promise<void> = Promise.resolve()

export function useKoreaScenarioData(cfg: KoreaConfig): KoreaScenarioData {
  const [payload, setPayload] = useState<KoreaScenarioPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [apiDown, setApiDown] = useState(false)
  const [failed, setFailed] = useState(false)
  const seq = useRef(0)

  useEffect(() => {
    const mySeq = ++seq.current
    const cancelled = () => seq.current !== mySeq
    setLoading(true)

    async function fetchStatic(preset: string) {
      const cached = bundleCache.get(preset)
      if (cached) return cached
      const r = await fetch(`/data/korea/scenarios/${preset}.json`)
      if (!r.ok) throw new Error(`korea bundle ${preset}: ${r.status}`)
      const p = (await r.json()) as KoreaScenarioPayload
      bundleCache.set(preset, p)
      return p
    }

    async function fetchLive() {
      const r = await fetch('/api/korea/run', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ preset: cfg.preset, levers: deviations(cfg),
                               overlays: cfg.overlays }),
      })
      if (!r.ok) throw new Error(`korea api: ${r.status}`)
      return (await r.json()) as KoreaScenarioPayload
    }

    if (isPristine(cfg)) {
      fetchStatic(cfg.preset)
        .then((p) => {
          if (cancelled()) return
          setPayload(p)
          setLoading(false)
          setFailed(false)
        })
        .catch(() => {
          if (cancelled()) return
          setLoading(false)
          setFailed(true)
        })
      return
    }

    const timer = setTimeout(() => {
      liveQueue = liveQueue.then(async () => {
        if (cancelled()) return
        try {
          const p = await fetchLive()
          if (cancelled()) return
          setPayload(p)
          setApiDown(false)
          setFailed(false)
        } catch {
          if (cancelled()) return
          setApiDown(true)
          try {
            const p = await fetchStatic(cfg.preset)
            if (!cancelled()) setPayload(p)
          } catch {
            if (!cancelled()) setFailed(true)
          }
        } finally {
          if (!cancelled()) setLoading(false)
        }
      })
    }, DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [JSON.stringify(cfg)])

  return { payload, loading, apiDown, failed }
}
