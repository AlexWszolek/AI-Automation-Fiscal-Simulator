// The always-on tornado's state machine, mirrored from the Streamlit fragment:
// pristine config -> instant precomputed entry (committed tornado.json);
// modified config -> 3s debounce -> POST /api/tornado -> 1s polling with progress,
// keeping the previous entry on screen grayed while the new one computes.
import { useEffect, useRef, useState } from 'react'
import { isPristine, slugFor } from '../lib/config'
import type { ScenarioConfig, TornadoEntry } from '../lib/types'

export interface TornadoState {
  entry: TornadoEntry | null
  stale: boolean                       // showing the previous config's entry while computing
  progress: { done: number; total: number } | null
  unavailable: boolean                 // modified config + compute service unreachable
}

const DEBOUNCE_MS = 3000
const POLL_MS = 1000

let staticIndex: Record<string, TornadoEntry> | null = null

async function staticEntry(slug: string): Promise<TornadoEntry | null> {
  if (!staticIndex) {
    const r = await fetch('/data/tornado.json')
    staticIndex = (await r.json()) as Record<string, TornadoEntry>
  }
  return staticIndex[slug] ?? null
}

export function useTornado(cfg: ScenarioConfig): TornadoState {
  const [state, setState] = useState<TornadoState>({
    entry: null, stale: false, progress: null, unavailable: false,
  })
  const seq = useRef(0)
  const lastEntry = useRef<TornadoEntry | null>(null)

  useEffect(() => {
    const mySeq = ++seq.current
    const live = () => seq.current === mySeq
    let pollTimer: ReturnType<typeof setTimeout> | undefined

    async function computeLive() {
      try {
        const started = await fetch('/api/tornado', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(cfg),
        }).then((r) => r.json() as Promise<{ job_id: string; status: string; result?: TornadoEntry; done?: number; total?: number }>)
        if (!live()) return
        if (started.status === 'done' && started.result) {
          lastEntry.current = started.result
          setState({ entry: started.result, stale: false, progress: null, unavailable: false })
          return
        }
        const poll = async () => {
          if (!live()) return
          const s = await fetch(`/api/tornado/${started.job_id}`).then((r) => r.json() as Promise<{ status: string; done: number; total: number; result?: TornadoEntry }>)
          if (!live()) return
          if (s.status === 'done' && s.result) {
            lastEntry.current = s.result
            setState({ entry: s.result, stale: false, progress: null, unavailable: false })
          } else if (s.status === 'error') {
            setState({ entry: lastEntry.current, stale: true, progress: null, unavailable: true })
          } else {
            setState({ entry: lastEntry.current, stale: lastEntry.current != null,
                       progress: { done: s.done, total: s.total }, unavailable: false })
            pollTimer = setTimeout(poll, POLL_MS)
          }
        }
        setState({ entry: lastEntry.current, stale: lastEntry.current != null,
                   progress: { done: started.done ?? 0, total: started.total ?? 150 },
                   unavailable: false })
        pollTimer = setTimeout(poll, POLL_MS)
      } catch {
        if (live()) setState({ entry: lastEntry.current, stale: true, progress: null, unavailable: true })
      }
    }

    if (isPristine(cfg)) {
      void staticEntry(slugFor(cfg)).then((e) => {
        if (!live()) return
        if (e) lastEntry.current = e
        setState({ entry: e, stale: false, progress: null, unavailable: false })
      })
      return
    }

    // modified config: gray the previous entry immediately, compute after the debounce
    setState({ entry: lastEntry.current, stale: lastEntry.current != null, progress: null, unavailable: false })
    const t = setTimeout(computeLive, DEBOUNCE_MS)
    return () => {
      clearTimeout(t)
      if (pollTimer) clearTimeout(pollTimer)
    }
  }, [cfg])

  return state
}
