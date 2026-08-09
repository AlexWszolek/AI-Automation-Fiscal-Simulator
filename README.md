# AI Automation Fiscal Model

A bottom-up accounting model of what AI-driven labor displacement does to United States public
finances, federal and state-and-local. Live at <https://aifiscalimpacts.alexwszolek.com>, with the
full technical report at `docs/report/report.docx`.

The question is narrower than what AI will do to the economy, as that question is too large to
answer and too vague to test. If AI automates some share of the work Americans currently do, what
happens to the public finances that depend on that work being done by taxed humans? The United
States raises roughly $5.0 trillion of federal revenue and $3.5 trillion of state and local revenue
against a $15.0 trillion compensation base, and eighty-four percent of federal receipts come from
individual income and payroll taxes, which are taxes on people being employed.

When a job is automated the wage leaves that base, but the value the job produced does not leave
with it. It re-emerges as corporate profit, as lower prices, or as capital income, each taxed at a
different and usually lower effective rate, and sometimes at no rate at all. The fiscal question is
therefore an accounting question about base migration, which is why this is built as an accounting
machine first: every dollar of displaced compensation is tracked to a destination, every destination
has a tax treatment, and the books are forced to balance by construction.

## What it finds

Three results hold across twelve differently-anchored scenarios.

The tax base migrates from labor to capital faster than output falls. Every destination of the saved
wage bill is taxed below the 25 to 40 percent combined marginal wedge on the wages it replaces, and
the largest leak is price reductions, which reach consumers and are recovered at roughly two cents
on the dollar through state consumption taxes.

Revenue falls faster than employment, as AI exposure concentrates in above-median-wage occupations,
so the workers displaced first carry more than their per-capita share of income tax and progressive
schedules do the rest.

The states are an asymmetric amplifier. The federal government meets lost revenue with deficits and
the states cannot, as nearly all must close their gaps within the year by raising rates on a
shrinking base or cutting spending, and both withdraw demand from the same economy that is shedding
jobs.

Two things about the scenario set are worth knowing before reading any single number. Five of the
twelve end with the federal balance better than baseline, so the fiscal problem is not automatic.
And what separates the good outcomes from the bad ones is mostly not how much work is automated but
what the labor market and the firms do with it, which matters for policy because the displacement
share is largely not a policy variable while the disposition of the saved bill largely is.

## The fiscal kernel

The kernel answers one question exactly: if this worker, in this occupation and this state, loses
this wage, what happens to every level of government? Five additive channels, each an independently
inspectable ledger line.

```
fiscal_delta(worker) =
    hand-rolled income tax   T_fed+state(HH_income) − T(HH_income − worker_wage)   # tax_side_schedule.xlsx
  + federal payroll          FICA(worker_wage)  with OASDI cap                     # tax_side_schedule.xlsx
  + PolicyEngine transfers   transfers(without worker) − transfers(with worker)    # baked OFFLINE lookup
  + corporate channel        displaced comp → operating surplus, taxed (partial)   # capital_income_by_sector.xlsx
  + consumption channel      eff. sales/excise rate × spending cut                 # taxable_consumption_base_by_state.xlsx
```

Taxes are hand-rolled from `tax_side_schedule.xlsx`, which is the transparent baseline the site
shows. PolicyEngine's tax output cross-checks that sheet, agreeing within a few percent, and is
never added to it, as adding it would double-count.

Transfers (EITC, refundable CTC, SNAP, Medicaid with expansion status, ACA subsidies, TANF, SSI) are
computed with PolicyEngine-US run offline into a static lookup, never called live. The marginal
object is `transfers(without) − transfers(with)`, so the EITC hump, the SNAP phase-out, and the
Medicaid cliff interact correctly rather than being averaged over.

Three modeling decisions carry most of the accuracy. The kernel integrates over the within-cell
income distribution rather than evaluating at the cell mean, as the tax and transfer deltas are
sharply nonlinear and the at-mean shortcut understates transfer deltas by a factor of 2.7 to 7.8 in
cells that straddle an eligibility threshold. It models both UI phases, computing the transfer delta
at household income including UI during the statutory window and with the worker at zero after
exhaustion, because the Medicaid and SNAP step-up mostly arrives at exhaustion rather than at
displacement. And the children distribution is resolved by filing status and state rather than by
occupation, as occupation-level cells are small and noisy while benefit rules are set by state.

## Architecture

| Module | Purpose |
|---|---|
| `fiscal_model/loaders.py` | Load the raw files into tidy frames keyed by SOC, sector, and state, units normalized. Control totals asserted on load; a load that does not reconcile fails before anything is computed. |
| `fiscal_model/rates.py` | Tax schedules from `tax_side_schedule.xlsx`: federal income by filing, payroll with caps, state brackets. Payroll is an ordered component list, so a second country supplies its own schemes without touching the engine. |
| `fiscal_model/kernel.py` | `fiscal_delta(...)`, pure and deterministic, unit-tested against control totals and quintile incidence. Built to exactness first. |
| `fiscal_model/levers.py` | Exposure → feasibility → adoption. Two independent exposure channels, cognitive (Yale PCA) and robotic (Webb 2020), combined multiplicatively. |
| `fiscal_model/dynamics_v2.py` | The stock-flow loop: seven worker states, disposition router, compute pool, survivor wages, shareholder channel, federal ledger, fifty-one-state closure, lagged demand. |
| `fiscal_model/invariants.py` | The nine conservation identities, asserted every period of every run. |
| `fiscal_model/presets.py` | Twelve literature-anchored scenarios and six composable policy overlays, with per-lever provenance. |
| `fiscal_model/country.py` | The facts that vary between national fiscal systems, with the US as the reference implementation. |

Build order matters here: `kernel.py` was built to exactness on one period before any dynamics were
wrapped around it, as a dynamics bug is otherwise indistinguishable from an accounting bug.

## Correctness

Two mechanisms, both enforced at runtime rather than in review.

Nine conservation identities hold on every period of every run, including every Monte Carlo draw:
worker headcounts partition the baseline per cell, the disposition of the saved bill sums exactly,
the federal deficit reconciles to its nineteen labeled components, state gaps close to numerical
residual zero. A run that violates any of them raises rather than reporting a number, and a new
fiscal flow that is not added to the reconciliation breaks the build, which is the point.

With every behavioral lever at its off value, the full multi-actor system reproduces the static
kernel bit for bit. Not approximately: the test is exact float equality, and it is differential, so
a shared re-base cannot mask a divergence. That anchor is what lets complexity be added lever by
lever without losing the ability to check the base case by hand.

The suite is 434 pytest plus 222 vitest.

## Setup

The runtime artifacts the model loads (NOC distribution, PolicyEngine benefit lookup and meta, UI
params, per-worker delta cache, roughly 5.6 MB under `data/interim/`) ship with the repo, so a fresh
clone runs out of the box.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest -q                    # 434 green = the clone is sound
.venv/bin/python -m fiscal_model.dynamics        # headline scenario, no npm needed
```

To regenerate the artifacts from source, after changing the bake, the NOC build, or kernel params,
one idempotent command rebuilds everything and downloads roughly 251 MB of ACS PUMS on first run:

```bash
bash scripts/bootstrap.sh
```

Two further committed artifacts the app reads: `data/raw/cbo_baseline_2026.csv`, the CBO Feb-2026
baseline extracted by `scripts/extract_cbo_baseline.py`, and `data/app_precomputed/mc_tornado.json`,
the presets' sensitivity tornados at N=200 seed 0. Regenerate the latter with
`scripts/precompute_app_mc.py` after any preset or lever change; a freshness test fails the suite if
it goes stale.

The full test suite needs these artifacts. Without them roughly five modules skip and `pytest`
prints a MISSING-ARTIFACT SKIPS summary, so a green run with hidden skips is obvious rather than
silent.

## Environment

Everything runs in `.venv` (Python 3.12, via `uv`), as system Python 3.14 lacks wheels for `pyarrow`
and `policyengine-us`. Use `.venv/bin/python` for all of it.

PolicyEngine is used offline only, in `scripts/bake_benefits.py`, to produce the static benefit
lookup. `fiscal_model` never imports it. Raw PUMS lives in `data/external/` and is gitignored.

## The website

The production site is a React/Vite/TypeScript static front end plus a small FastAPI compute
service. Presets and their policy-response combinations are precomputed and committed under
`web/public/data/`, so the site browses fully offline, and the API serves custom slider values and
modified-config sensitivity tornados.

Everything the TypeScript side knows about the model is generated from `fiscal_model/app_params.py`
by `scripts/gen_web_bundle.py`, covering the widget grid, URL-codec golden vectors, and scenario
bundles, with a freshness test that fails if it drifts. One Python function,
`fiscal_model/webpayload.py`, produces both the static bundles and every API response, so static and
live agree by construction rather than by discipline. User-facing copy is hand-maintained in
`web/src/content/copy.json`.

```bash
cd web && npm install && npm run dev          # front end
.venv/bin/uvicorn api.main:app --port 8000    # compute service
```

Deployment examples (nginx/Caddy plus systemd) are in `deploy/`. Building with
`VITE_HIDE_TORNADO=1 npx vite build` drops the sensitivity section entirely, with no tornado.json
fetch and no API jobs; a plain `npx vite build` restores it.

The Streamlit prototype at `app/streamlit_app.py` predates the site and still runs locally, but
nothing generates from it any more and its deployment has been deleted. `app/redirect_stub.py`
remains so that old links forward with their full query string if it is ever redeployed.

## Reproducing the report

Every number, table, and figure in `docs/report/report.docx` is generated by a seeded pipeline. The
prose cites numbers only through `{{n:...}}` placeholders resolved against a generated
`manifest.json`, and the build fails on any unresolved reference, so the text cannot cite a number
the model did not produce.

```bash
.venv/bin/python scripts/report_artifacts.py     # ~40 min: 12 scenarios at N=1000, validation, screening
.venv/bin/python scripts/build_report_docx.py    # assembles the document
```

`scripts/global_screening.py` sweeps a 10,000-point Latin hypercube over the full lever space,
asserting the conservation battery at every sampled point and producing the global tornado and
fiscal regime map reported in §7.14.

## Known simplifications

The report's Section 10 carries the full table with a direction of bias for each. The ones most
worth knowing before using any number:

- The corporate channel books full conversion of saved compensation into taxable surplus, which is a
  deliberate steelman of the recovery and therefore **understates** the fiscal gap.
- Robotics is anchored to the current robot-patent stock, so even at full physical feasibility the
  dexterity, care, and performance occupations sit near zero. This is a current-technology floor
  that **understates** a true post-AGI scenario.
- Capital income does not spend: retained profit reaches the economy only through tax, never through
  shareholder consumption or investment.
- There is no task creation. Displaced workers re-enter only through a fixed re-employment rate into
  a finite set of low-exposure occupations, so automation never endogenously creates new kinds of
  work.
- Benefits are entitlement values rather than take-up-adjusted spending, and are looked up by total
  household income rather than earned income, which overstates transfer outlays and understates EITC
  deltas respectively.
- UI parameters are national defaults rather than per-state DOL schedules, and transfer federal-state
  splits are flat rather than following the actual FMAP range.

The first two cut against the model's own thesis, which is the more demanding test: correcting either
in the direction the evidence points would widen the gap rather than narrow it.
