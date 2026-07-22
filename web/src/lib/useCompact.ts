// Small-screen flag for the two chart variants that need it (tornado label truncation, map
// height). CSS handles everything else — this hook exists only because vega specs cannot
// media-query; ChartPanel's ResizeObserver re-fits the chart when the flag flips.
import { useEffect, useState } from 'react'

const QUERY = '(max-width: 640px)'

export function useCompact(): boolean {
  const [compact, setCompact] = useState(() => matchMedia(QUERY).matches)
  useEffect(() => {
    const mq = matchMedia(QUERY)
    const onChange = () => setCompact(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return compact
}
