# One-pager evidence base — Korea presentation

**How to use this.** Every row is a claim you can put on the one-pager, with the number, the
primary source (document + table, all in `sources/` unless noted), and the caveat that travels
with it. Nothing here is ⚠; everything traces to a ✓ row in `korea-fiscal-system.md` or a
test-pinned model result in `../KOREA_PRESET_EVIDENCE.md`. The prose is yours — this file is
the answer to "where is that from?" for every sentence you might write. Source strings are
formatted to paste directly into a footnote.

---

## 1. The thesis in one statistic

| Claim | Number | Source | Caveat / note |
|---|---|---|---|
| Social security contributions are Korea's single largest tax revenue source | **30.2% of total taxation (2024)**; personal income tax 20.1%; tax-to-GDP 25.3% | OECD, *Revenue Statistics 2025* | Levied exclusively on labour; earmarked to funds with their own actuarial balances |
| The earmarking consequence | Revenue lost to automation leaves **actuarially committed funds**; corporate-tax recapture lands in the **general account**; no mechanism moves it back without legislation | Institutional structure: 국민연금법 / 국민건강보험법 / 고용보험법 (fund-based, own accounts) | This is the institutional-damage argument — state it as structure, not projection |
| The honest complication (pre-empt it) | Korea's corporate tax take is high: **14.4% of total taxes (2023)** vs OECD 11.8%, G7 9.0% | OECD Revenue Statistics (via research doc §1) | Say it before someone in the room does: recapture is real — but it refills the wrong account |

## 2. Three funds, three deadlines — one already passed

| Claim | Number | Source | Caveat / note |
|---|---|---|---|
| The Employment Insurance benefit account is effectively exhausted now | Reserve ratio **0.1×** against the statutory **1.5–2×** (고용보험법 §84); FY2025 benefit spending **₩17.46tn** (record); account reserves ₩1.73tn nominal, **−₩5.99tn net of public-fund borrowings** | NABO, 2025회계연도 결산 위원회별 분석 [기후에너지환경노동위원회], p.~200 (`nabo-settlement-fy2025-labor-committee.pdf`) | Statutory bands are **per account**: the employment-stabilization account is above its own band (1.7×) — it is precisely the account that pays displacement benefits that is empty |
| Whole EI fund, FY2025 | Balance **−₩592bn**; reserves ₩7.80tn nominal / **₩79.6bn** net of borrowings | 「2026 대한민국 사회보험」 [표 149], citing MOEL 「2025회계연도 고용보험기금 결산보고서」 (2026-06) (`nabo-social-insurance-2026.pdf`) | |
| The stated cause is this model's mechanism | "Employment fell, so contribution revenue fell, while benefit spending rose" | Same sources (settlement analysis) | Already running for demographic/cyclical reasons — before AI displacement at scale |
| Health insurance depletes within the planning horizon | Deficit from **2026**; cumulative reserves depleted **2031** on the natural trend, **2029** with the medical-reform investment plans; annual balances −₩5.2/−8.0/−9.4/−8.7tn (2026–29); ten-year position −₩27.8tn vs baseline | NABO Focus 제162호 (2026-06-09), 표 4 + 그림 1–2 (`nabo-focus-162-nhi-reestimate-2026-2035.pdf`) | Lead with this fund: 2029 is inside a sitting official's horizon |
| The pension reform bought eight years | Pre-reform depletion **2057** (NABO Focus 92, 2025-02-27); post-reform **2065**, deficit transition 2047 (NABO 현안보고서 2025-06, [표 25]) | `nabo-focus-92-longterm-2025-2072.pdf`; `nabo-pension-reform-analysis-2025.pdf` | Quote NABO's **2065**, not the ministry-attributed "~2064" in press coverage. Reform: 9%→13% by 2033 (first increase in 28 years), replacement 43%, passed 2025-03-20 |

## 3. What automation does — the model's contribution (all with bands)

Config for every row: BOK-published exposure × three anchored adoption presets (ramp to 2035,
flat after) × the documented wage-linked-share band edges, run through the **assembled V2
model** — net displacement (re-employment, survivor raises, demand destruction) with **EI
benefit outlays included**. Matches `web/public/data/korea.json` (parity-tested); the bridge
is pinned in `tests/test_korea_assembly.py`.

| Claim | Number | Source | Caveat / note |
|---|---|---|---|
| Automation pulls the health fund's depletion forward | **0.23–0.90 years** across the full band (central preset: 0.42–0.57) | Model: published NHI path (Focus 162) × assembled erosion | Small BY CONSTRUCTION — the fund is nearly dead already; automation's sharper NHI expression is post-depletion deficit widening |
| Automation takes back part of what the pension reform bought | **0.49–2.44 of the eight bought years** (central preset: **0.96–1.30**) | Model: published post-reform NPS path ([표 25]) × assembled erosion | The unit the audience already reasons in; adoption held flat after 2035 (conservative on a 2065 horizon) |
| The EI fund's planned rebuild falls short | Planned reserves of ₩21.8tn by 2029 fall **₩2.6–11.4tn short** (central ≈ ₩5.5tn) | Model: NABO mid-term EI baseline ([표 151]) × assembled erosion + benefit outlays | The outlay side dominates (revenue-only central was ≈₩1.5tn); the published rebuild itself relies on planned public-fund borrowing |
| A fast AI world is qualitatively different | Korinek-Suh translations: AGI-in-20y pulls NHI **1.25y** forward, gives back **3.82** bought pension years, EI shortfall **₩17.1tn**; AGI-in-5y: **2.14y / 6.59 years / ₩59.2tn** (vs ₩21.8tn planned) | Model: `korea-agi-*` presets, mid shares | Cognitive channel only — **understates** manual-occupation displacement; separate scenario rows, never inside the band |
| Even the optimistic AI scenario breaks the fiscal path | Structural: contributions are levied per employed worker, not on output | Argument, not model output (research doc §5.1) | Cancellation acts on output; the fiscal problem acts on the tax base. No model needed — say it verbally |

## 4. Which institution takes the hit — composition

| Claim | Number | Source | Caveat / note |
|---|---|---|---|
| Korea's AI-cognitive displacement wave is clerical-centred | 사무 종사자 = **17.4% of all employment**, and under the BOK classification **wholly high-exposure / low-complementarity** (displacement-prone) | BOK 이슈노트 2025-2 「AI와 한국경제」, <그림 9> (figure-read, reconciled to the note's published 24%/27% aggregates; confirmed by IMF SIP 2025/013 Fig. 7) (`bok-issue-note-2025-2-ai-korean-economy.pdf`) | The complementarity split respects exposure ≠ displacement: professionals are mostly the augmentation case (16.0 of 21.6pp high-complementarity) |
| Which occupations automate determines which institution pays | Pension contributions capped at ₩6.59m/month (~2× median): high-wage automation → income-tax loss (general account); low-wage automation → full-proportional fund loss — and the **pension base is relatively bottom-heavy**, so low-wage automation erodes NPS proportionally hardest | Cap: NPS notice (기준소득월액 상·하한, 2026-07); asymmetry: model-derived, test-pinned (`test_korea_funds.py`) | Label the asymmetry as model arithmetic on the statutory cap, not an external estimate |
| In the central scenario the damage spreads evenly | ≈9% erosion across institutions by 2035 (funds 9.1%, capped NPS slightly worst at 9.2%, income tax 9.1%) | Model, central preset (assembled) | The clerical epicentre is mid-wage — the sharp splits appear under concentrated what-ifs, not the central case. Survivor raises recover progressive income tax slightly faster than the capped pension base — the cap asymmetry survives assembly |

## 5. Context numbers that may earn a place on the sheet

| Claim | Number | Source |
|---|---|---|
| Combined social-insurance burden, rising by law | **≈20.9% of payroll (2026) → ≈24.4% by 2033** vs US FICA 15.3% | 2026 rates: 보건복지부/MOEL notices + 「2026 대한민국 사회보험」; path = legislated pension phase-in |
| Local government rides national revenue by statute | **40.03%** of national internal taxes (19.24% Local Share Tax + 20.79% Local Education Subsidy) | KDI/재정통계 BRIEF (research doc §4) |
| VAT headroom exists on the Korinek instrument | **10%**, unchanged since 1977; 15.3% of revenue vs OECD 20.5% | OECD Revenue Statistics |
| Why the safety-net question is live | Elderly poverty **38.1% (2022)** — highest in OECD (avg 14.2%); public social spending 15.2% of GDP, rank 34/38 | OECD via research doc §3/§5 |
| The fiscal baseline any result sits on | Debt-to-GDP **47.8% (2025) → 173.0% (2072)**; scenario band 163.2–181.9% | NABO Focus 제92호 (`nabo-focus-92-longterm-2025-2072.pdf`) |
| Korea sits early on the AI adoption curve | **31% of SMEs** use AI vs >50% in Germany (OECD survey, Oct–Dec 2024) | OECD/KLI, *AI and the Labour Market in Korea* (2025), Box 2.1 (`oecd-ai-labour-market-korea-2025.pdf`) |
| The technical ceiling is not the constraint | **38.8% of jobs >70% task-automatable at 2023 technology; ~99% at the 2030 expert forecast** | KDI Research Monograph 2023-03 (`kdi-monograph-2023-03-ai-labor-en.pdf`) — feasibility, NOT adoption; realization is gated by adoption |

## 6. The scope box (print it, don't remember it)

| Disclosure | Statement |
|---|---|
| Coverage | Wage employees only, ~**76% of employment** (self-employment 23.9%, 6th-highest OECD — treated qualitatively; it is Korea's de facto old-age safety net and already the fastest-automating sector) |
| Data frame | Establishment survey: **12.4m of ~22m wage workers**, larger firms over-represented, no public administration |
| Granularity | 9 occupation groups × 24 wage brackets (**deliberately coarse, transparently so**) — the public-data ceiling; wage distribution beats per-cell means for progressive taxes |
| Displacement | **Net**: the assembled model re-employs into the finite service floor, pays survivor raises, and propagates demand destruction — the direct gross ceiling is retained only for structural what-ifs, labeled as such |
| Erosion | Revenue side plus **EI benefit outlays**; still ignores NHI/NPS outlay responses and forgone investment income (both understate the damage) |
| AGI scenarios | Cognitive channel only — no published Korean robot-exposure vector; understates manual-occupation displacement (disclosed wherever shown) |
| Exposure | Figure-read from BOK's published chart, accepted only because it reconciles with the note's printed aggregates; ±0.5pp read error carried into the band |
| Shares | NHI and NPS wage-linked revenue shares shown as bands (0.65–0.97 / 0.75–0.95) pending two statistical splits — the bands are IN the headline ranges |
| Net direction | Biases run in both directions and are stated; the presentation quotes ranges, not points |

## 7. The prepared verbal answers (sourced)

- **"Korea needs automation — we have no workers."** Cancellation operates on *output*;
  the fiscal problem operates on the *tax base* (contributions per employed worker). They do
  not net out. Even AI-goes-well breaks the fiscal plumbing as wired. (Research doc §5.1 —
  argument, no model required.)
- **"Exposure studies say white-collar; observed effects hit the young and low-skilled."**
  Correct — exposure ≠ realized displacement (OECD 2025 finds exactly this split). The model
  uses the complementarity-adjusted displacement-prone share, not raw exposure, and the
  composition results are presented as scenario arithmetic, not prediction.
- **"Your own projection says the funds die anyway."** Yes — that is the point. The deadlines
  are NABO's, not ours. The model adds only what arithmetic cannot: how far automation moves
  them, what that costs the reform Korea just paid for, and which institution bleeds first.
