// The Korea sensitivity section: Spearman tornado from the joint MC, target-selectable
// across the three fund headlines. Pristine presets read the committed tornado bundle;
// modified configs POST /api/korea/tornado synchronously (the Korea engine is fast enough
// to skip the US job queue) with a 1s settle and the last entry shown stale while loading.
import { useEffect, useRef, useState } from 'react'
import { koreaTornado } from '../charts/korea'
import { ChartPanel } from '../components/ChartPanel'
import { ListBox } from '../components/ListBox'
import { TORNADO_LABELS } from '../charts/labels'
import { fmt, KOREA_GRID } from './config'
import type { LocalePack } from './locale'
import { deviations, isPristine, type KoreaConfig } from './config'



interface TornadoData {
  config: { preset: string; levers: Record<string, number>; n: number }
  base: Record<string, number>
  targets: Record<string, { lever: string; spearman: number }[]>
}

const staticCache = new Map<string, TornadoData>()
const DEBOUNCE_MS = 1000

export function KoreaTornadoSection({ cfg, pack }: { cfg: KoreaConfig; pack: LocalePack }) {
  const KO = pack.KO
  const T = KO.templates as Record<string, string>
  const TARGETS = KO.tornado_targets as Record<string, string>
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
            (l) => (KOREA_GRID[l] ? pack.lever(KOREA_GRID[l].copy).label
                                  : (TORNADO_LABELS[l] ?? l)),
            TARGETS[target], { stale })}
          caption={`${KO.captions.tornado} — ${fmt(T.tornado_caption_suffix, { n: entry.config.n })}`}
        />
    </div>
  )
}
