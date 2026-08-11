// The Korea sensitivity section: Spearman tornado from the joint MC, target-selectable
// across the three fund headlines. Pristine presets read the committed tornado bundle;
// modified configs POST /api/korea/tornado synchronously (the Korea engine is fast enough
// to skip the US job queue) with a 1s settle and the last entry shown stale while loading.
import { useEffect, useRef, useState } from 'react'
import copy from '../content/copy.json'
import { koreaTornado } from '../charts/korea'
import { ChartPanel } from '../components/ChartPanel'
import { ListBox } from '../components/ListBox'
import { TORNADO_LABELS } from '../charts/labels'
import { deviations, isPristine, KOREA_GRID, leverCopy, type KoreaConfig } from './config'

const KO = (copy as any).korea
const TARGETS = KO.tornado_targets as Record<string, string>

interface TornadoData {
  config: { preset: string; levers: Record<string, number>; n: number }
  base: Record<string, number>
  targets: Record<string, { lever: string; spearman: number }[]>
}

const staticCache = new Map<string, TornadoData>()
const DEBOUNCE_MS = 1000

export function KoreaTornadoSection({ cfg }: { cfg: KoreaConfig }) {
  const [entry, setEntry] = useState<TornadoData | null>(null)
  const [stale, setStale] = useState(false)
  const [target, setTarget] = useState('ei_shortfall_tn')
  const seq = useRef(0)

  useEffect(() => {
    const mySeq = ++seq.current
    const cancelled = () => seq.current !== mySeq
    setStale(true)

    async function fetchStatic() {
      const cached = staticCache.get(cfg.preset)
      if (cached) return cached
      const r = await fetch(`/data/korea/tornado/${cfg.preset}.json`)
      if (!r.ok) throw new Error(`korea tornado ${cfg.preset}: ${r.status}`)
      const t = (await r.json()) as TornadoData
      staticCache.set(cfg.preset, t)
      return t
    }

    if (isPristine(cfg)) {
      fetchStatic()
        .then((t) => {
          if (cancelled()) return
          setEntry(t)
          setStale(false)
        })
        .catch(() => { if (!cancelled()) setStale(false) })
      return
    }

    const timer = setTimeout(() => {
      fetch('/api/korea/tornado', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ preset: cfg.preset, levers: deviations(cfg) }),
      })
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
        .then((t: TornadoData) => {
          if (cancelled()) return
          setEntry(t)
          setStale(false)
        })
        .catch(() => { if (!cancelled()) setStale(false) })   // keep last entry, un-stale
    }, DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [JSON.stringify(cfg)])

  if (!entry) return null
  const rows = entry.targets[target] ?? []
  return (
    <div className="col-wide">
      <div className="panel">
        <h2>{KO.sections.tornado}</h2>
        <div className="picker" style={{ maxWidth: '22rem', marginBottom: '0.5rem' }}>
          <ListBox
            ariaLabel="Sensitivity target"
            value={target}
            options={Object.entries(TARGETS).map(([value, label]) => ({ value, label }))}
            onChange={setTarget}
          />
        </div>
        <ChartPanel
          spec={koreaTornado(rows,
            (l) => (KOREA_GRID[l] ? leverCopy(l).label : (TORNADO_LABELS[l] ?? l)),
            TARGETS[target], { stale })}
          caption={`${KO.captions.tornado} — n=${entry.config.n} draws around this configuration`}
        />
      </div>
    </div>
  )
}
