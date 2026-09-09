// The Korea sensitivity section: Spearman tornado from the joint MC, target-selectable
// across the three fund headlines. Pristine presets read the committed tornado bundle;
// modified configs POST /api/korea/tornado synchronously (the Korea engine is fast enough
// to skip the US job queue) with a 1s settle and the last entry shown stale while loading.
import { useEffect, useRef, useState } from 'react'
import { koreaTornado } from '../charts/korea'
import { ChartPanel } from '../components/ChartPanel'
import { ListBox } from '../components/ListBox'
import { TORNADO_LABELS } from '../charts/labels'
import { fmt, KOREA_GRID, TORNADO_ONLY_REFS } from './config'
import type { LocalePack } from './locale'
import { deviations, isPristine, type KoreaConfig } from './config'



interface TornadoData {
  config: { preset: string; levers: Record<string, number>; n: number }
  base: Record<string, number>
  targets: Record<string, { lever: string; spearman: number }[]>
}

const staticCache = new Map<string, TornadoData>()
// a live tornado is seconds of MC on the server: wait for the user to stop moving
// sliders before asking for one (runs no longer queue behind it, but every request
// still costs the box)
const DEBOUNCE_MS = 2000
const RETRY_MS = 1500

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

    // the tornado samples the PRE-POLICY model and ignores the tax mults, so a config that
    // differs from its preset only on those is pristine for its purposes: the committed
    // n=400 bundle, not a live n=150 draw whose lower ranks would visibly reshuffle
    const TORNADO_INERT = new Set(['income_tax_mult', 'corp_tax_mult', 'cons_tax_mult',
                                   'vat_pp', 'nps_mandate_share', 'corp_to_funds'])
    const sampled = Object.keys(deviations(cfg)).filter((k) => !TORNADO_INERT.has(k))
    if (isPristine(cfg) || sampled.length === 0) {
      fetchStatic()
        .then((t) => {
          if (cancelled()) return
          setEntry(t)
          setStale(false)
        })
        .catch(() => { if (!cancelled()) setStale(false) })
      return
    }

    let retryTimer: ReturnType<typeof setTimeout> | undefined
    const request = (attempt: number): Promise<TornadoData> =>
      fetch('/api/korea/tornado', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ preset: cfg.preset, levers: deviations(cfg) }),
      })
        .then((r): Promise<TornadoData> => {
          if (r.ok) return r.json() as Promise<TornadoData>
          // 409: another viewer's request superseded ours; 429: the queue was full.
          // Neither means our configuration was computed — try once more, then give up.
          if ((r.status === 409 || r.status === 429) && attempt === 0 && !cancelled())
            return new Promise<void>((res) => { retryTimer = setTimeout(res, RETRY_MS) })
              .then(() => (cancelled() ? Promise.reject(new Error('cancelled')) : request(1)))
          return Promise.reject(new Error(String(r.status)))
        })
    const timer = setTimeout(() => {
      request(0)
        .then((t: TornadoData) => {
          if (cancelled()) return
          setEntry(t)
          setStale(false)
        })
        .catch(() => { /* keep the last entry, and keep it DIMMED: it is not this config */ })
    }, DEBOUNCE_MS)
    return () => { clearTimeout(timer); clearTimeout(retryTimer) }
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
                    : TORNADO_ONLY_REFS[l] ? pack.lever(TORNADO_ONLY_REFS[l]).label
                    : (TORNADO_LABELS[l] ?? l)),
            TARGETS[target], { stale })}
          caption={`${KO.captions.tornado} — ${fmt(T.tornado_caption_suffix, { n: entry.config.n })}`}
        />
    </div>
  )
}
