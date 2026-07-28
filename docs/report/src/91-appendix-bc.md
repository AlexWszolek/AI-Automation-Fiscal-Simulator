{{section:landscape}}

# Appendix B — The twelve scenarios, as shipped

Scenarios are rows, levers columns, split across two tables to stay legible. Values not shown
inherit the shipped defaults, identical in every scenario: reabsorption rung 1 (service-floor), UI
26 weeks, raise ceiling 1.5, spillover 0.5, offshore share 0, `automation_tax_rate` 0 (taxation is a
composable overlay, never a scenario), and the four shareholder-channel levers at their measured
current-law anchors (price/earnings multiple 16, taxable-holder share 0.27, realization rate 0.04,
effective rate on realized gains 0.19). Two values are grid-snapped from their sources — Windfall
`lfp_exit_rate` 0.033 → 0.03 and capital effective rate 0.267 → 0.27. Per-lever provenance is in
`fiscal_model/presets.py` and `docs/PRESET_EVIDENCE.md`.

In the adoption column **†** marks a parametric kink (linear to the end value by the reach year, flat
after) and **‡** a path threaded piecewise-linearly through trajectory points the source itself
publishes; unmarked is linear across the whole horizon.

| Scenario | cog / phys feas. | rob. lag | adoption | reach yr | horizon | reab. / haircut | lfp exit / attrition | Baumol / crowding |
|---|---|---|---|---|---|---|---|---|
| ①Acemoglu | 0.2/0.05 | 8 | 0.02→0.23 | — | 10 | 0.5/0.13 | 0.03/0.025 | 0/0 |
| ②Brynjolfsson | 0.3/0.1 | 6 | 0.02→0.3 | — | 10 | 0.6/0.1 | 0.02/0.025 | 0/0 |
| ③Windfall | 0.55/0.2 | 5 | 0.05→0.5 | — | 10 | 0.3/0.3 | 0.03/0.025 | 0/0 |
| ④China-Shock | 0.3/0.2 | 4 | 0.05→0.4 | — | 15 | 0.075/0.25 | 0.1/0.04 | 0/0 |
| ⑤AGI-20y | 1/1 | 10 | 0.05→1 | — | 20 | 0.05/0.4 | 0.05/0.025 | 0/0 |
| ⑥AGI-5y | 1/1 | 2 | 0.2→1 † | 5 | 10 | 0.05/0.4 | 0.1/0.025 | 0/0 |
| ⑦AI-2027 | 1/0.9 | 3 | 0.2→1 † | 5 | 8 | 0.1/0.4 | 0.05/0.025 | 0/0 |
| ⑧2040 Plan A | 0.95/0.95 | 9 | 0.05→1 ‡ | 9 | 14 | 0.15/0.3 | 0.05/0.025 | 0/0 |
| ⑨2040 Plan D | 1/0.95 | 6 | 0.05→1 ‡ | 7 | 10 | 0.05/0.4 | 0.1/0.025 | 0/0 |
| ⑩Karger rapid | 0.6/0.15 | 8 | 0.03→0.16 | — | 10 | 0.35/0.13 | 0.06/0.025 | 0.3/0 |
| ⑪Metaculus | 0.55/0.2 | 7 | 0.02→0.2 | — | 10 | 0.45/0.12 | 0.04/0.025 | 0.35/0.1 |
| ⑫OpenAI | 0.75/0.05 | 10 | 0.05→0.2 † | 7 | 10 | 0.55/0.12 | 0.03/0.025 | 0/0 |

| Scenario | retained/price/surv. | auto_cost / compute ETR | surv. elasticity | prod. / price passthru | demand mult. | growth / interest | state cut / cap | start yr |
|---|---|---|---|---|---|---|---|---|
| ①Acemoglu | 0.6/0.35/0.05 | 0.05/0.1 | 0 | 0.15/0.3 | 0.3 | 0.04/0.03 | — | 2026 |
| ②Brynjolfsson | 0.55/0.25/0.2 | 0.1/0.1 | +0.10 | 0.5/0.3 | 0.3 | 0.045/0.03 | — | 2026 |
| ③Windfall | 0.5/0.5/0 | 0.1/0.27 | −0.15 | 0.3/0.5 | 0.5 | 0.04/0.03 | — | 2026 |
| ④China-Shock | 0.7/0.2/0.1 | 0.1/0.1 | −0.30 | 0.2/0.3 | 1.5 | 0.035/0.03 | — | 2026 |
| ⑤AGI-20y | 0.8/0.15/0.05 | 0.15/0.05 | −0.50 | 0.9/0.5 | 1 | 0.06/0.04 | 0.5/0.5 | 2026 |
| ⑥AGI-5y | 0.8/0.15/0.05 | 0.2/0.05 | −0.50 | 0.9/0.5 | 1.5 | 0.08/0.04 | 0.5/0.5 | 2026 |
| ⑦AI-2027 | 0.7/0.2/0.1 | 0.3/0.05 | −0.50 | 0.9/0.5 | 1.2 | 0.08/0.04 | — | 2026 |
| ⑧2040 Plan A | 0.55/0.3/0.15 | 0.3/0.05 | +0.10 | 0.9/0.5 | 1 | 0.08/0.04 | 0.5/0.5 | 2027 |
| ⑨2040 Plan D | 0.8/0.15/0.05 | 0.3/0.05 | −0.50 | 0.9/0.5 | 1.5 | 0.08/0.04 | 0.5/0.5 | 2027 |
| ⑩Karger rapid | 0.55/0.25/0.2 | 0.15/0.1 | 0 | 0.95/0.3 | 0.3 | 0.05/0.03 | — | 2026 |
| ⑪Metaculus | 0.45/0.2/0.35 | 0.1/0.1 | 0 | 0.45/0.3 | 0.5 | 0.04/0.03 | — | 2026 |
| ⑫OpenAI | 0.55/0.3/0.15 | 0.15/0.1 | 0 | 0.35/0.3 | 0.45 | 0.04/0.03 | — | 2026 |

The survivor share is derived, never set: it is the remainder of the disposition simplex after
retained profit and price reduction, which is why the three always sum to one. A blank state
entry means the scenario leaves the default closure (rate hikes first, cuts for the remainder);
`0.5/0.5` means half the gap closes by spending cuts under a 50 percent rate-hike feasibility cap,
the configuration the AGI-class scenarios use because labor-base rate hikes cannot close
AGI-stage gaps.

{{pagebreak}}

# Appendix C — Fiscal summaries, the external comparator

Complete per-year fiscal summaries and four-channel decompositions for all twelve scenarios are in
the artifact CSVs (`docs/report/artifacts/presets/<key>/summary_tax.csv` and
`summary_channel.csv`) and are browsable in the web application. Reproduced here is the Windfall
Trust comparator, because Section 9.1's replication argument needs its numbers in-document: the
full fiscal summary, then the channel view that decomposes the same run into the four migration
paths the report's first thesis names.

{{tbl:summary_tax:windfall-medium|full|Windfall Trust — Medium, full fiscal summary ($B, all years).}}

{{tbl:summary_channel:windfall-medium|full|Windfall Trust — Medium, four-channel decomposition ($B): labour→capital, resident→non-resident, taxable→consumer-surplus, government spending.}}

{{section:portrait}}
