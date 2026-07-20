// ScenarioPayload — mirrors fiscal_model/webpayload.py (the single producer).
export type LeverValue = number | boolean | string

export interface ScenarioConfig {
  preset: string | null
  overlays: string[]
  levers: Record<string, LeverValue>
}

export interface SummaryRow {
  group: string
  label: string
  kind: string
  values: (number | null)[]
  total: number | null
}

export interface SummaryView {
  years: number[]
  rows: SummaryRow[]
}

export interface OverlayReadout {
  key: string
  name: string
  no_gap: boolean
  recovered_B: number
  gap_B: number
  pct: number | null
}

export interface StateRow {
  state: string
  fips: number
  net_B: number
  revenue_loss_pct: number
  shortfall_B: number
  rate_hike_B: number
  spending_cut_B: number
  implied_rate_hike_pct: number
  taxable_base_B: number
  at_cap: boolean
}

export interface ScenarioPayload {
  config: {
    preset: string | null
    overlays: string[]
    levers: Record<string, LeverValue>
    start_year: number
    n_periods: number
    cfg_repr: string
    modified_fields: string[]
    overlay_notes: string[]
  }
  rows: Record<string, number>[]
  final: {
    jobs_lost_M: number
    employment_drop_pct: number
    inc_tax_lost_cum_B: number
    fed_deficit_abs_B: number
    fed_deficit_abs_pct_gdp: number
    fed_debt_B: number
    fed_deficit_B: number
    state_gap_B: number
    productivity_index: number
    ubi_required_rate: number
    n_states_capped: number
  }
  grounding: Record<'jobs' | 'revenue_flow' | 'debt_stock' | 'fed_deficit_flow' | 'state_flow' | 'real_gdp', string>
  states: StateRow[]
  state_calc: { tax_base_B: number; implied_pct: number }
  summary: Record<'tax_busd' | 'tax_pct' | 'channel_busd' | 'channel_pct', SummaryView>
  scale_check: {
    final_year: number
    cbo_deficit_B: number
    add_pct: number
    cbo_max_year: number
    extrapolated: boolean
  }
  overlay_readouts: OverlayReadout[]
  overlay_readouts_combined?: { recovered_B: number; gap_B: number; pct: number }
  warnings: {
    kink_replaced: boolean
    ubi_unfunded?: { ubi_annual: number; required_rate: number }
  }
}

export interface TornadoEntry {
  tornado: { lever: string; spearman: number }[]
  p10: number
  p50: number
  p90: number
  n: number
}
