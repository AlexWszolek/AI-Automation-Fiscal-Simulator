# Design: the shareholder windfall channel (dividend + capital-gains recapture)

**Status: design pass — not yet implemented.** Necessity-test verdict: PASS — a first-order
federal revenue line currently booked at $0 (shareholder-level tax on the equity claim the
automation surplus creates), on the causal path to the headline, with every parameter an
externally measured quantity. No parameter is calibrated against the model's own targets.

## The objection this design answers

"You cannot project equity prices." Correct — and the channel never does. It prices the
*incremental claim* the automation surplus creates, conditionally, the same way the corporate
offset already steelmans full conversion of saved compensation to taxable surplus:

- The model already computes the after-tax profit increment (by C2 conservation, wherever in
  the economy it lands — AI vendors or downstream firms with lower COGS; the disposition split
  is the lever that says how much surplus lands as profit *anywhere* vs prices).
- A capitalization multiple converts a *permanent* earnings increment into paper wealth. The
  multiple is a disclosed convention anchored to observed market P/E, not a forecast.
- The measured holder/realization structure then does the real work: only ~a quarter of US
  corporate equity sits in taxable accounts; realizations run a few percent of the accrued
  stock per year (deferral + step-up-at-death are *why* measured realization is slow); the
  effective rate on qualified dividends and LTCG is the same statutory schedule.

The finding is robust to the one unmeasurable input (the multiple) because the bottleneck is
the measured leakage chain: ~6 cents/yr of federal tax per dollar of retained earnings at
steady state, even at generous multiples. If the answer were sensitive to the multiple the
channel would be dubious; it is not, and showing that *is the point*.

## Mechanism (dynamics layer only — no kernel/bake change)

Everything derives from existing labeled columns; `E` is the after-tax new permanent earnings
level accruing to shareholders:

```
E_t      = retained_profit_B − corp_offset_B − automation_tax_B − swf_revenue_B     # existing columns
ΔE_t     = max(0, E_t − E_{t−1})                 # increment to the permanent level (E_{−1} = 0);
                                                 # max(0) books gains only — the steelman direction
div_tax_t = dividend_payout_share · E_t · equity_taxable_share · shareholder_eff_rate      # flow leg
ΔV_t     = equity_pe_multiple · (1 − dividend_payout_share) · ΔE_t                  # new accrued value
G_t      = G_{t−1} + equity_taxable_share · ΔV_t − R_t          # taxable unrealized windfall stock
R_t      = cg_realization_rate · G_{t−1}                        # realizations (t=0 realizes nothing)
cg_tax_t = shareholder_eff_rate · R_t
```

Notes:
- **After-tax base for free**: `retained_profit` is the pre-tax partition leg (C2); netting the
  three taxes the model already books on it (corporate offset, robot tax, SWF share) gives the
  shareholder claim with zero new assumptions.
- **One-time capitalization**: each year capitalizes only the *increment* ΔE to the permanent
  earnings level — never re-capitalizes the standing stream. The saved bill is persistent (a
  job stays automated), which is what makes the P/E treatment legitimate.
- **Dividends vs gains split**: the payout share is taxed as a flow in the year earned; only
  the retained share is capitalized and deferred. This is the Modigliani–Miller-clean
  bookkeeping that avoids taxing the same dollar twice at the shareholder level. Deferral is
  the fiscal story — it is why the recovery is small.
- **Step-up at death** is not a separate parameter: measured realization rates already reflect
  deferral behavior including hold-until-step-up. Cited as the reason the rate is low.
- **Buybacks**: economically part of payout but taxed as realizations (+1% IRA excise). Folded
  into the retained/CG leg; the omitted excise is a small understatement of recovery,
  disclosed in §10.
- **Within-preset monotonicity**: adoption is cumulative and disposition shares are constant,
  so E_t is (near-)monotone; `max(0, ·)` only guards pathological corners.
- **A2 rule**: the channel is nominal; the price level never touches it.
- **Baseline CG revenue** (~$200B+/yr) is already in the receipts base; the channel books only
  the *windfall delta* — consistent with the model's delta accounting and the t=0 rate gate.

## Levers (5 new V2Params fields — all shipped at measured anchors, none calibrated)

| lever | shipped anchor (fetch-verified where noted) | off value (C8) |
|---|---|---|
| `equity_pe_multiple` | **16** — long-run S&P mean P/E 16.23 / median 15.08 (multpl/Shiller, VERIFIED). Current market is far richer (trailing 28.5, CAPE 40.4 as of 2026-07) — using the long-run mean is the conservative convention; the current-market alternative is a disclosed sensitivity | 0 |
| `dividend_payout_share` | **0.32** — Damodaran S&P payout ratio 31.1% (2022) / 32.0% (2023), VERIFIED. Buybacks (2024 record $942.5B, ~60% of the $1.57T total cash return, VERIFIED) are folded into the CG leg — sellers realize gains when tendering — which is why the realization anchor leans above its historical floor | 0 |
| `equity_taxable_share` | **0.27** — Rosenthal–Mucciolo 2024 (Tax Notes Federal, VERIFIED): taxable-account share of US stock 27% in 2022 (79% in 1965); the 2016 Rosenthal–Austin canonical gives 24.2% (2015). Foreigners 42%, retirement ~27% — the leak is structural and growing | — (inert at pe=payout=0) |
| `cg_realization_rate` | **0.04** — the citable stock-based rate is 3.1%/yr (Gravelle–Lindsey 1960–84, via Treasury OTA WP-66, VERIFIED: "only 3.1 percent of the stock of accrued gains was realized in any given year"); modern arithmetic (~$2T realized 2021 over a ~$40–50T unrealized stock) runs ~4–5% and buyback churn argues the upper half — 0.04 splits the difference, band 0.03–0.05. CBO cross-check: realizations revert to 3.7% of GDP long-run (VERIFIED) | — (inert) |
| `shareholder_eff_rate` | **0.19** — Treasury OTA taxes-paid table (VERIFIED): average effective rate on realized gains 19.4% in 2013–14 (the current 23.8%-top-rate regime); modern extension ~17–19% (Tax Foundation/CBO, FY-CY mismatch caveat noted). Qualified dividends share the schedule | — (inert) |

Supporting color (VERIFIED, Liscow–Fox/Yale 2025): the largest holders recognize ~4% of their
economic income — the slow-realization story is not a modeling convenience, it is measured.
Step-up at death (why realization stays low): CBO's parameter has 47% of accrued gains on
corporate stock never realized; CRS models "approximately half" (R47113, VERIFIED); the
exclusion's tax expenditure was ~$99B by 2024 (Treasury OTA, VERIFIED). Baseline scale check:
federal CG receipts ran $186B (FY2020) / $305B (FY2021) / $336B (FY2022) — the line the model
currently books at zero *delta* is one of the federal ledger's larger items.
Omitted: the 1% IRA buyback excise (IRC §4501, JCT $74B/10y, VERIFIED) — a small understatement
of recovery, §10-disclosed. Full verbatim quotes + URLs: shareholder-channel-evidence-raw.json.

`DEFAULTS_V1REDUCTION`: pe = 0, payout = 0 → both legs vanish exactly → C8 preserved.
MC: all five join PERTURBED at the ±15% convention. Presets: no overrides — current law,
inherited from DEFAULTS_SHIPPED everywhere; provenance lands in the global lever table
(PRESET_EVIDENCE §1) + raw-json quotes, not per-preset.

## Correctness surface

- **Columns**: `shareholder_div_tax_B`, `shareholder_cg_tax_B`, `shareholder_windfall_stock_B`
  (G), `shareholder_realized_B` (R).
- **C6**: two new subtractive lines (`− div_tax − cg_tax`); the reconciliation breaks loudly
  if either is dropped.
- **New invariant (C-sh)**: the stock ledger — `G_t − G_{t−1} = taxable_share·pe·(1−payout)·ΔE_t
  − R_t`, `cg_tax = rate·R_t`, `div_tax = payout·E_t·taxable_share·rate` — asserted per period
  alongside C1–C8.
- **Reduction**: v1 has no channel; off values zero every new column → bit-parity holds.
- **Summary table** (`summary.py`): one new revenue row; its self-reconciliation gains the two
  columns.
- **Sanity magnitude** (final anchors; to be confirmed at implementation): per $1 of after-tax
  new profit level, dividends yield 0.32·0.27·0.19 ≈ 1.6¢/yr immediately and the CG leg
  0.68·16·0.27·0.04·0.19 ≈ 2.2¢/yr once accrued — **≈ 3.8¢/yr per windfall dollar at steady
  state**. AGI-5y-scale worlds (E ≈ $7T): ~$150–250B/yr by the final year, comparable to
  compute-parity; windfall-medium: tens of $B; modest worlds: single-digit $B. The 96 % leak
  (non-taxable holders × deferral × the labor-vs-capital rate gap) IS the base-migration thesis,
  now with its largest missing line priced.

## Blast radius (the V2Params-field regen checklist)

New fields change `cfg_repr` → **every** precomputed artifact regenerates: 624-config app
tornado (~100 min), 624 scenario bundles, grid.json + codec vectors (URL codec gains fields),
web pages. All preset numbers move (channel on by default — it is current law). Tests: C6/C8
sweeps, sampler domains, goldens re-baseline **by intent** (modeling change, not optimization).

## Sequencing decision (open — Alex)

The mechanism + tests can land immediately, but the moment it merges, the live app's numbers
diverge from the report's frozen manifest until the report redo (which also carries the
ai-2027 re-time to reach≈4–5/start 0.2 per the Davidson evidence rationale, and the
12-preset report scope). Options:
1. Land now, regen app artifacts, report catches up at the redo (interim divergence, disclosed).
2. Hold the merge; land mechanism + redo as one batch (no divergence, later app improvement).

## Explicitly out of scope

- State-side CG/dividend taxation (follows the pass-through federal-only convention; §10 line).
- Behavioral realization response to rate changes (no rate changes are modeled).
- Sector-heterogeneous holder bases (holder structure is economy-wide; C2 makes the aggregate
  the right object).
- Equity price *levels*, market multiples responding to rates, or any forecast of either.
