# Korea port — project brief

**Read this first if you are picking up the Korea work with no prior context.**
Detailed verified research: `docs/research/korea-fiscal-system.md` (666 lines, ✓ = verified with
source, ⚠ = pending primary verification — respect that distinction, it is load-bearing).

---

## 1. What this project is

This repo is the **AI Automation Fiscal Simulator** — a bottom-up US model of what AI automation
does to public finances, pricing every displaced worker's taxes and benefits across ~33,000
occupation × state cells, live at `aifiscalimpacts.alexwszolek.com`.

The Korea project ports that model to South Korea for a **presentation to senior Korean
policymakers in early September 2026**, arranged through an AI-safety diplomacy organisation run
by former senior diplomats.

**Alex may not deliver the talk himself** — the organisation may present it. That single fact
drives most of the artifact design: everything must survive a presenter who does not know the
model's internals and cannot improvise a caveat.

Deliverables, in order of importance: a **one-pager** policymakers keep (Alex's voice — see rules),
**slides showing the website with outcomes**, and the **interactive website** as credibility proof.

---

## 2. Why Korea — the argument the model has to serve

Do not treat this as "the US model with Korean numbers." The thesis is structural.

**Korea's single largest tax revenue source is social security contributions: 30.2% of all
taxation** (2024, OECD Revenue Statistics), ahead of personal income tax at 20.1%. It is levied
entirely on labour. And it is **earmarked** — it funds schemes with their own actuarial balances,
not general revenue.

So automation in Korea does not merely shift revenue from a heavily-taxed base to a lightly-taxed
one. It moves money **out of actuarially-committed funds into the general account**, and nothing
moves it back without new legislation. Rising corporate tax receipts cannot refill the pension
fund. That is an institutional failure, not a rounding error, and it is what a finance ministry
can actually act on.

**Three funds, three deadlines — one already passed:**

| Fund | Status |
|---|---|
| **Employment Insurance** | **Effectively exhausted now** — 0.1× its statutory 1.5–2× reserve ratio, 16 years running |
| National Health Insurance | Reserves depleted **2029–2030** |
| National Pension | ~2064, after the 2025 reform (9%→13% by 2033) bought ~8 years |

The Employment Insurance finding is the strongest single item, because of *why* it is empty:
**fewer workers paying in while more draw out.** That is this model's mechanism, already running in
Korea for demographic reasons, before AI displacement at scale. The fund that would pay for AI
displacement is already empty.

**Four supporting findings that shape the design:**

- **Damage lands on different institutions depending on which occupations automate.** Income tax is
  highly concentrated (33% of wage earners pay zero, but only 0.13% above ₩80m; top 1% pay ~31% of
  the tax) while pension contributions are **capped** at ~2× median earnings. High-wage automation
  → big income-tax loss, capped insurance loss → hits the **general account**. Low-wage automation
  → negligible income tax, full proportional insurance loss → hits the **earmarked funds**.
- **The US state-austerity amplifier has a cleaner Korean analogue.** Not "absorbed nationally":
  local budgets are statutorily **40.03% of national internal taxes** (19.24% Local Share Tax +
  20.79% Local Education Subsidy). One elasticity, no political reaction functions — *easier* to
  model than 51 balanced budgets. Drop the provincial layer; keep the formula.
- **Self-employment (23.9%) is Korea's de facto old-age safety net** — retail, food service,
  transport; saturated; ₩141tn in debt; already the sector automating fastest. This is the model's
  existing **finite refuge** mechanism, binding far harder than in the US. If it closes, people land
  on Basic Pension and NBLSS — the outlay side of the same budget.
- **Cancellation vs compounding is settled verbally, not by modelling.** The obvious objection is
  "Korea *needs* automation, we have no workers." Answer: cancellation acts on **output**; the
  fiscal problem acts on the **tax base**; Korea taxes labour income, so output rescued by capital
  is fiscally invisible. **Even the optimistic AI scenario breaks the fiscal path.** Do not build a
  mechanism for this.

---

## 3. What is already done (5 commits, on `main`, UNPUSHED)

| Commit | What |
|---|---|
| `e88faf8` | Korea fiscal-system research doc — 42 verified claims |
| `bc27dcf` | KOSIS data probe — access solved, granularity constrained |
| `be4802c` | Payroll engine takes a component list, not the hardcoded US schema |
| `ee076b4` | `fiscal_model/country.py` — the country seam, US as reference |
| `c25ebfc` | Declining baseline (`V2Params.demography_path`) |

**382 pytest + 222 vitest green.** Working tree clean except `docs/website_copy_round2.xlsx`
(Alex's, untracked, do not commit — and never commit the `~$` Excel lock file).

### 3.1 Data access — SOLVED, with one constraint

`kosis.kr` deep links bounce through an SSO handshake and its English tree is a JS accordion that
resists scripting. **But MOEL mirrors the same tables with no login, as plain scrapeable HTML:**

```
https://stathtml.moel.go.kr/statHtml/statHtml.do?orgId=118&tblId=<ID>&conn_path=I2
```

| Table | Content | Vintage |
|---|---|---|
| `DT_118N_PAYN42` | **Industry** × education × age × sex: mean wage + worker count | ✓ 2020–2025 |
| `DT_118N_PAYM39` | **Occupation** × sex × **wage bracket** × age: worker count + hours | ✓ 2020–2025 |
| `DT_118N_PAYM22` | Occupation × ... mean wage | ⚠ **DEAD — ends 2015** |

**The constraint: public tables carry only the 10 KSCO major groups**, not minor-group level,
against 832 SOC cells in the US model. Softened two ways: `PAYM39` gives a **25-bracket wage
distribution rather than a mean** (better for progressive tax; 10 × 25 = 250 cells, above the
50–150 budgeted), and finer KSCO is available by **microdata application** (마이크로데이터신청 via
`laborstat.moel.go.kr`) — Korean-language, unknown turnaround, route via the diplomacy org.

2025 totals for calibration (`PAYM39`): 12,413,858 wage workers — managers 120,892; professionals
3,669,625; clerks 3,447,778; service 960,008; sales 561,179; agriculture 28,684; craft 758,694;
machine operators 1,835,977; elementary 1,031,019. Mean monthly wage ₩4,482k (`PAYN42`).
**This is an establishment survey**: ~12.4m of roughly 22m wage workers nationally, skewed to
larger firms. Disclose it.

### 3.2 Code seams now in place

- **`fiscal_model/country.py`** — `Country` dataclass with `US` as reference implementation and a
  test pinning it to the live constants. Key field: `subnational_mode`
  (`balanced_budget` = US, `formula_transfer` = Korea at 40.03%, `none`). Korea is **not yet
  populated** — that is the next batch.
- **`rates.PayrollFICA`** takes an ordered component list. Three shapes cover Korea's five schemes:
  `capped` (pension, health), `flat` (employment, industrial accident), `surcharge` (unused there).
  `_PayrollFICALegacy` is retained as the bit-parity reference — do not delete it.
- **`V2Params.demography_path`** — per-period working-age population scale factors relative to
  year 0. `None` = flat = today's US behaviour. Structural, so automatically `FROZEN` in `mc.py`.

---

## 4. Standing rules — these are not negotiable

1. **Push only on Alex's explicit word.** Commit locally at phase boundaries. Never `git push`
   unprompted.
2. **Never write or "improve" user-facing site copy.** It ports byte-for-byte via extraction
   (`scripts/extract_web_copy.py`). Report prose and `docs/research/` analysis ARE model-authored
   and in scope. **The one-pager is Alex's voice** — supply the evidence base, not the pitch.
3. **The necessity test** gates every mechanism change: it must fix a specific wrong NUMBER, sit on
   the causal path to the fiscal headline, and be anchored to something external. Ideally it
   *removes* a free parameter. FAILS: new dynamics on an already-roughly-right channel with
   parameters calibratable only against the model's own targets. If an effect is only visible
   inside the tornado band, it is false precision. See
   `~/.claude/.../memory/necessity-test-for-model-changes.md` if available.
4. **Bit-parity discipline for optimisations**: keep the old implementation as an in-repo reference
   with a permanent bitwise anchor test (see `mc.run_mc`, `survivor._delta_loop`,
   `reabsorption._delta_loop`, `rates._PayrollFICALegacy`). Never re-derive tax math in a different
   float-op order.
5. **Scope, already decided and disclosed**: national-only; **wage employees only** (~76% of Korean
   employment — self-employment is 23.9% and must be a headline caveat, not a footnote); ~50–150
   occupation cells, not 33,000. "Deliberately coarse, transparently so" is defensible before this
   audience; "approximately right about your provinces" is not.

---

## 5. Repo gotchas that will bite you

**Adding ANY `V2Params` field stales THREE artifact families** — all key on a repr-exact `cfg_key`,
and this fires **even when no number changes**, because every artifact embeds a repr of the whole
dataclass. Rebuild all three or the suite stays red:

```bash
.venv/bin/python scripts/precompute_app_mc.py --workers 12   # ~35 min, 624 configs
.venv/bin/python scripts/gen_web_bundle.py                   # fast, 624 bundles
.venv/bin/python scripts/report_artifacts.py                 # ~35-45 min FULL build
```

Miss the third and you get exactly one stray failure (`test_report_manifest::
test_numerics_match_source`) after the first two look clean. `--stage render` will NOT fix it.
Defaults (n=1000, spread 0.15, seed 0) match the committed build — do not override them.

**Batch your field additions into one regeneration.** Korea parameterisation will add several;
paying ~80 minutes of compute per field is a real velocity tax.

**The right verification gate** for a field addition is *"every model NUMBER identical, artifacts
regenerated"* — NOT "bundles byte-identical", which is impossible. Verify by diffing regenerated
bundles against `git show HEAD:...` and confirming the only changed leaf path is
`config.cfg_repr`. That is exactly what was verified for `c25ebfc`, across all 624.

**Other traps:** new `V2Params` fields default to `FROZEN` in `mc.py` (add to `PERTURBED` only if
they should be MC-perturbed — `demography_path` should NOT be); preset lever values must sit on the
widget grid (`test_ui_grid_representability`); new revenue flows must join BOTH `_tax_rows` AND
`_channel_rows` in `summary.py` or the channel reconciliation assert kills every overlay bundle.

---

## 6. What to build next, in dependency order

**Blocked on Alex / the org (highest priority, unblocks everything below):** three primary
documents — Employment Insurance fund accounts from MOEL, NABO's 2023–2032 health and long-term
care projection, NABO's 2025–2072 long-term fiscal projection. All three headline claims currently
rest on press coverage of these, and they are also *inputs* to item 4 below. PDF fetching defeated
the tooling; a human likely needs to download them.

1. **Korea cell structure** from `PAYM39` (occupation × wage bracket) + `PAYN42` (industry).
   This is where the port becomes real.
2. **`KOREA` country descriptor** — five social-insurance components via the new payroll list
   (2026: pension 9.5% capped at ₩6.59m/month → 13% by 2033, health 7.19%, long-term care 0.9448%,
   employment 1.8%, industrial accident 1.47% ≈ **20.9% of payroll**, reaching ~24.4% by 2033);
   `formula_transfer` subnational mode at 40.03%; Korean transfer programmes (Basic Pension,
   NBLSS, EITC).
3. **Populate `demography_path`** from Statistics Korea 장래인구추계 2022–2072: working-age share
   71.1% (2022) → 66.6% (2030) → 51.9% (2050) → 45.8% (2072). The mechanism exists; it needs
   numbers.
4. **Fund-balance projector — the missing piece behind the headline metric.** The intended headline
   is *"automation pulls the depletion date forward by N years"*, because Korea already reasons in
   those units and it survives a presenter who does not know the internals. But the model produces
   a **wage-base erosion path**, not a fund balance, and **no trust-fund machinery exists**
   (`government.py` has a revenue ledger and state closure, nothing else). Needed: take the fund's
   published contribution/outlay path, scale contributions by the eroded base, re-accumulate, find
   the zero crossing. ~100–200 lines, but requires the primary documents above.
5. **Exposure join** using Korea-native measures — KDI's routinisation index on the 2020 Korea
   Dictionary of Occupations, or the East Asian Economic Review KR–US industry comparison — rather
   than a KSCO→SOC crosswalk. Better methodologically *and* rhetorically: importing US O*NET scores
   into Korea is the most obvious line of attack in the room.
6. **Korea scenarios** calibrated against KDI / OECD / Metaculus, with per-field provenance recorded
   the way `docs/PRESET_EVIDENCE.md` does for the US. Calibration input: Korean AI adoption is low
   by international standards — **31% of SMEs vs over 50% in Germany** — so Korea sits *earlier* on
   the adoption curve than peers.

---

## 7. Known risks, stated plainly

- **The model may not be the load-bearing deliverable.** The three fund deadlines are *arithmetic*,
  not model output; the strongest single number (0.1× reserve ratio) needs no model at all. The port
  earns its place only by producing what arithmetic cannot: the depletion-date shift (item 4), the
  composition of damage across institutions, the demographic–automation interaction, the uncertainty
  band, and quantified policy comparisons.
- **Two existing overlays land in Korea with real institutions attached**, which is unusually
  lucky: `fed-vat` (Korea's VAT is 10%, frozen since 1977, 15.3% of revenue vs OECD 20.5% — genuine
  headroom on the instrument Korinek recommends) and `swf` (the National Pension Fund is >₩1,200tn
  and already a major institutional equity holder, so "let the fund capture the windfall" is a
  mandate question, not a thought experiment).
- **Exposure vs realised displacement differ** and you will be asked. OECD finds most-*exposed*
  occupations are white-collar professionals and managers; observed Korean employment effects fall
  on younger, lower-skilled workers. Do not conflate them.
- **A half-built model in front of Korean officials is worse than none** — they know their fiscal
  system better than we do, and any error becomes the story. If the primary documents do not arrive
  within about a week, re-scope to the briefing-paper version: US model as demonstrated method plus
  a rigorous Korea section built on the verified arithmetic. The argument survives intact.
- **Everything institutional in the research doc marked ⚠ needs primary verification** before it
  appears in an external artifact. The ✓/⚠ convention is there precisely so this does not get lost.
