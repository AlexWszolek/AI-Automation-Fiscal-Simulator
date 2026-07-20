// The headline metrics: two heroes (Employment −%, cumulative federal income tax lost) and six
// second-tier figures, each with its grounding line in a fixed-height slot so the row never
// reflows. Labels/help are the app's (content/copy.json).
import copy from '../content/copy.json'
import { dollarsB, dollarsHero, pct, signed, thousands } from '../lib/format'
import type { ScenarioPayload } from '../lib/types'
import { HelpTip } from './controls'

const METRIC_HELP: Record<string, string | null> = Object.fromEntries(
  (copy.metrics as { label: string; help: string | null }[]).map((m) => [m.label, m.help]),
)

function Metric({ label, value, ground, hero }: {
  label: string
  value: string
  ground?: string
  hero?: boolean
}) {
  return (
    <div className={hero ? 'metric hero' : 'metric'}>
      <div className="metric-label caption">
        <HelpTip label={label} help={METRIC_HELP[label] ?? null} />
      </div>
      <div className="metric-value num">{value}</div>
      <div className="metric-ground caption">{ground ?? ' '}</div>
    </div>
  )
}

export function MetricGrid({ p }: { p: ScenarioPayload }) {
  const f = p.final
  const g = p.grounding
  return (
    <>
      <div className="metric-row heroes">
        <Metric hero label="Employment" value={pct(-f.employment_drop_pct)}
                ground="share of the 154.0M modeled workforce" />
        <Metric hero label="Federal income tax lost (cumulative)"
                value={dollarsHero(f.inc_tax_lost_cum_B)} ground={g.revenue_flow} />
      </div>
      <div className="metric-tier">
        <Metric label="Jobs lost (final yr)" value={`${thousands(f.jobs_lost_M, 1)}M`} ground={g.jobs} />
        <Metric label="Federal deficit (final yr)" value={dollarsB(f.fed_deficit_abs_B)}
                ground={`= ${thousands(f.fed_deficit_abs_pct_gdp, 1)}% of GDP`} />
        <Metric label="Federal debt (Δ cumulative)" value={dollarsB(f.fed_debt_B)} ground={g.debt_stock} />
        <Metric label="Net fiscal impact (final yr)" value={`${signed(-f.fed_deficit_B)}B`}
                ground={g.fed_deficit_flow} />
        <Metric label="State shortfall (final yr)" value={dollarsB(f.state_gap_B)} ground={g.state_flow} />
        <Metric label="Real GDP effect" value={signed(100 * (f.productivity_index - 1), 1) + '%'}
                ground={g.real_gdp} />
      </div>
    </>
  )
}
