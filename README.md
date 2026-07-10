# AI Automation Fiscal Model

An **interactive, user-driven model of the fiscal effects of AI/automation** on the U.S.
economy — federal *and* state-and-local. A user sets levers (how much of each
occupation/industry is automated, how fast, reabsorption rate, state budget response,
optional UBI) and sees the downstream consequences: lost tax revenue, rising transfer
outlays, deficits, and distributional/structural shifts.

**Design philosophy:** every assumption is a *user-set lever*, never baked in. Credibility
comes from the *accounting being correct*. The chain — automation → lost compensation → lost
income tax → lost demand → second-round effects — is inspectable, with offsets (reabsorption,
capital-income recirculation, productivity) shown at the same prominence as costs:
**cost, offset, net**.

**Thesis the accounting surfaces:** under serious automation the tax base **migrates from
labor to capital**. Labor income is taxed at a high, top-heavy effective rate; capital income
lower. Because the most AI-exposed work is high-wage cognitive work, **revenue can fall faster
than employment**, while automatic-stabilizer outlays rise and **states must balance their
budgets** (a contractionary amplifier the federal government doesn't face).

See `docs/PROJECT_BRIEFING_v2.md` for the full briefing and data dictionary.

## The fiscal kernel — division of labor (kept separate & additive, each lever inspectable)

```
fiscal_delta(worker) =
    hand-rolled income tax   T_fed+state(HH_income) − T(HH_income − worker_wage)   # tax_side_schedule.xlsx
  + federal payroll          FICA(worker_wage)  with OASDI cap                     # tax_side_schedule.xlsx
  + PolicyEngine transfers   transfers(without worker) − transfers(with worker)    # baked OFFLINE lookup
  + corporate channel        displaced comp → operating surplus, taxed (partial)   # capital_income_by_sector.xlsx
  + consumption channel      eff. sales/excise rate × spending cut                 # taxable_consumption_base_by_state.xlsx
```

- **Taxes** are hand-rolled from `tax_side_schedule.xlsx` (the transparent baseline the website
  shows). PolicyEngine's tax output is used **only** to cross-check this sheet (agree within a
  few %), never added — no double counting.
- **Transfers** (EITC, refundable CTC, SNAP, Medicaid w/ expansion status, ACA subsidies, TANF,
  SSI) are computed with **PolicyEngine-US run offline** into a static lookup table; the marginal
  object is `transfers(without) − transfers(with)` so the EITC hump, SNAP phase-out, and Medicaid
  cliffs interact correctly. Never called live from the site.

## Confirmed modeling decisions

1. **Integrate over the within-cell income distribution**, not the cell mean. The household file
   gives a *mean* household income per occupation×state×filing; the tax and transfer deltas are
   sharply nonlinear (EITC hump, SNAP phase-out, Medicaid cliff), so we scale OEWS wage percentiles
   to the household mean (§3.7) and integrate across a few percentile points per cell.
2. **Model both UI phases.** Means-tested benefits key off current income and UI counts as income,
   so the transfer delta is computed at two residual points: household income *including UI* (during
   the ~26-week window) and with the worker at $0 (post-exhaustion). The Medicaid/SNAP step-up
   happens at UI *exhaustion*, not at displacement.
3. **NOC granularity = by filing-status × state**, derived from ACS PUMS NOC (robust vs noisy
   occupation-level small cells; state matters for benefit rules).

## Architecture (build order)

| Module | Purpose |
|---|---|
| `fiscal_model/loaders.py` | Load the 8 files → tidy DataFrames keyed by SOC/sector/state, units normalized. Assert control totals on load (fail loud). |
| `fiscal_model/rates.py` | §5 schedules from `tax_side_schedule.xlsx` — federal income by filing, payroll w/ caps, state brackets; corporate by sector; consumption by state. |
| `fiscal_model/kernel.py` | `fiscal_delta(...)` — pure, deterministic, unit-tested vs control totals & quintile incidence. **Built to exactness first.** |
| `fiscal_model/levers.py` | exposure → feasibility → adoption transform → per-occupation displacement flows. Two **independent** exposure channels — cognitive (Yale PCA) and robot (Webb 2020), combined multiplicatively. |
| `fiscal_model/dynamics.py` | stock-flow loop: cohorts, UI exhaustion, deficit accumulation, state balanced-budget. |
| `fiscal_model/validate.py` | reconciliation: control totals, quintile incidence (T43), PolicyEngine aggregates. |

> Build and test **`kernel.py` to exactness first** (one period, no dynamics), then wrap in
> dynamics — a dynamics bug is otherwise indistinguishable from an accounting bug.

## Control totals (BEA 2024 — asserted on load)

- Employment grand total **163,223k** (observed 163,218k — 0.003% gap, to confirm)
- Compensation **$15,049,121m** · Value added (GDP) **$29,298,075m**
- Corp profits before tax **$3,721,572m** · Nonfarm proprietors **$1,652,676m**

## Status

- [x] Project scaffold, canonical data files copied to `data/raw/`
- [x] Data reconnaissance + cross-file join-key checks (8 file specs + 3 join checks)
- [x] `loaders.py` — all 8 files, units normalized, **control-total assertions pass**
- [x] `rates.py` — tax engine from params, **reproduces the baked schedules to ±$0.5**
- [x] `tests/` — 37 regression tests green (`pytest`)
- [x] `kernel.py` skeleton — tax + **corporate** + **consumption** channels, fed/state split, cost/offset/net, transfer seam (`set_transfer_lookup`)
- [x] **Part A** — `noc.py`: P(children \| filing, state, income band) from raw 2024 ACS PUMS (`csv_hus`), WGTP-weighted, cell-size fallback ladder → `data/interim/noc_distribution.csv`
- [x] **Part B** — `scripts/bake_benefits.py` (PolicyEngine, offline in `.venv`) → `data/interim/benefit_lookup.parquet` (138k rows); `transfers.py` interpolates + differences it, splits fed/state, wired into the kernel seam
- [x] **Part C** — `integrate.py`: within-cell expectation over income × NOC × residual phase; **kink acceptance test passes** (integrated transfer Δ is 2.7–7.8× the at-mean Δ for cliff-straddling cells)
- [x] **Part B.6** — tax cross-check ✓ (PE vs `tax_side_schedule` within 2.5% = the 2024/2025 bracket vintage gap; payroll exact ex-state-SDI). Aggregate reconciliation run (`scripts/validate_transfers.py`) — interpretive, see simplifications
- [x] `levers.py` — exposure→feasibility→adoption transform; two **independent** channels combined multiplicatively: cognitive (Yale PCA) and robot (Webb 2020 robot-patent exposure, `data/raw/robot_exposure_by_soc.xlsx`)
- [x] `dynamics.py` — stock-flow loop: precomputed per-worker deltas (occ×state, cached) + cohorts, UI exhaustion, reabsorption, demand multiplier, federal debt w/ interest, **state balanced-budget**, UBI required-rate; demo reproduces both theses (revenue falls faster than employment; federal cushioned by capital recapture, states bear an unfinanceable gap)
- [x] **66 regression tests green** (incl. numeric anchors for the consumption/corporate channels, worker-conservation, lognormal quadrature, and the Medicaid-cliff driver)
- [x] **Website** — `app/streamlit_app.py`: light report-style theme, static labeled charts with captions, collapsible lever groups with per-lever help, two headline rows (jobs lost, cumulative income-tax loss, GDP effect, …), a state section (shortfall-before-response + hardest-hit table), and tax-regime dials (income/capital/consumption ×)
- [x] **Scenario presets** — `fiscal_model/presets.py`: 7 literature-anchored world states (Acemoglu → AI-2027) + 4 composable policy overlays (robot taxes at the literature optimum, UBI, compute parity), fetch-verified anchors in `docs/PRESET_EVIDENCE.md`; every preset passes the conservation battery
- [x] **Technical report + global screening** — `docs/report/report.docx` (data → equations → findings across the 7 scenarios; every prose number resolved from a generated `manifest.json` so text and model can't drift) built by `scripts/report_artifacts.py` + `scripts/build_report_docx.py`; `scripts/global_screening.py` sweeps a 10,000-point Latin hypercube over the full 26-lever space (invariants on every point, global tornado, fiscal regime map — report §7.9)

### Complete: model backend + website
`loaders → rates → kernel (5 channels) → transfers → integrate → levers → dynamics → app`, all tested (66 tests).

**Run the app:**  `.venv/bin/streamlit run app/streamlit_app.py`
**Headline scenario (CLI):**  `.venv/bin/python -m fiscal_model.dynamics`

## Setup (fresh clone)
The model and app need a Python 3.12 venv plus three regenerable, gitignored artifacts
(NOC distribution, PolicyEngine benefit lookup, per-worker delta cache). One idempotent
command builds everything (downloads ~251 MB of ACS PUMS on first run):

```bash
bash scripts/bootstrap.sh
```

Step by step: `uv venv --python 3.12 .venv` → `uv pip install --python .venv/bin/python -r requirements.txt`
→ download PUMS into `data/external/` → `python -m fiscal_model.noc` →
`uv pip install --python .venv/bin/python -r requirements-bake.txt && python scripts/bake_benefits.py`
→ `python -m fiscal_model.dynamics` (precompute). Core deps live in `requirements.txt`; the heavy,
offline PolicyEngine bake is pinned separately in `requirements-bake.txt`.

> The full test suite needs these artifacts; without them ~5 modules skip and `pytest` prints a
> **MISSING-ARTIFACT SKIPS** summary, so a green run with hidden skips is obvious.

## Environment
- Main code runs in **`.venv` (Python 3.12, via `uv`)** — system Python 3.14 lacks wheels for
  `pyarrow`/`policyengine-us`. Use `.venv/bin/python` for everything.
- **PolicyEngine** is used **offline only** (`scripts/bake_benefits.py`) to produce the static
  `benefit_lookup`; `fiscal_model` never imports it. Raw PUMS in `data/external/` (gitignored).

### Known v1 simplifications to revisit
- Pass-through (proprietor) capital tax is routed **federal-only**; individual income tax is really fed+state, so this overstates the federal offset / understates state recapture.
- Corporate channel assumes lost compensation converts to operating surplus at `surplus_capture` (default 1.0 = most generous offset, per "steelman the optimistic case").
- **UI params**: national defaults (45% replacement, 26 wks, $20k cap) — needs real per-state DOL data.
- **Transfer fed/state split**: flat shares (Medicaid 65/35, TANF 50/50, SNAP/EITC/CTC/ACA federal, SSI 95/5); Medicaid FMAP actually varies 50–77% by state.
- **Benefit values are entitlement/eligibility amounts** (PE = eligibility × per-enrollee value, per plan Part B) — the right object for the marginal "what becomes available on displacement," but they overstate *actual* program spending where take-up < 100% (esp. ACA PTC). A take-up lever would reconcile aggregate levels.
- **B.6 aggregate reconciliation undershoots actual program totals** because (a) the bake models working-age, non-disabled representative households, so Medicaid/SSI/SNAP — dominated by aged/disabled/LTC — are under-represented, and (b) benefits are looked up by total household income (HINCP) rather than earned income, understating aggregate EITC. The marginal *mechanics* are validated (kink test + tax cross-check); reconciling *levels* needs an earned-income axis + take-up adjustment.
- **Robotics is anchored to the *current* robot-patent stock** (Webb 2020 `pct_robot`), so even `physical_feasibility=1` leaves dexterity/care/performance jobs (barbers, surgeons, actors) near zero — a current-technology floor that *understates* a true post-AGI scenario. The `robotics_maturity` lever (inert in v1) is the hook to interpolate toward a physical-task-content ceiling (O*NET) when that data is wired.
