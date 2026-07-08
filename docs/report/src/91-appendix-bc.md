{{section:landscape}}

# Appendix B — The seven scenarios, as shipped

Values not shown inherit the shipped defaults. All presets run the service-floor reabsorption
engine; the AGI-5y adoption path is kinked (full automation at year 5, flat thereafter). Two
values are grid-snapped from their sources (Windfall lfp 0.033→0.03, capital ETR 0.267→0.27);
provenance for every value is carried in `fiscal_model/presets.py` and `docs/PRESET_EVIDENCE.md`.

| Lever | ①Acemoglu | ②Brynjolfsson | ③Windfall | ④China-Shock | ⑤AGI-20y | ⑥AGI-5y | ⑦AI-2027 |
|---|---|---|---|---|---|---|---|
| cognitive / physical feasibility | .20/.05 | .30/.10 | .55/.20 | .30/.20 | 1.0/1.0 | 1.0/1.0 | 1.0/.90 |
| robotics_lag (years) | 8 | 6 | 5 | 4 | 10 | 2 | 3 |
| adoption start→end | .02→.23 | .02→.30 | .05→.50 | .05→.40 | .05→1.0 | .20→1.0 | .10→1.0 |
| horizon (years) | 10 | 10 | 10 | 15 | 20 | 10 | 8 |
| reabsorption / haircut | .50/.13 | .60/.10 | .30/.30 | .075/.25 | .05/.40 | .05/.40 | .10/.40 |
| lfp_exit / attrition | .03/.025 | .02/.025 | .03/.025 | .10/.04 | .05/.025 | .10/.025 | .05/.025 |
| retained/price/survivor | .60/.35/.05 | .55/.25/.20 | .50/.50/.00 | .70/.20/.10 | .80/.15/.05 | .80/.15/.05 | .70/.20/.10 |
| auto_cost / compute ETR | .05/.10 | .10/.10 | .10/.27 | .10/.10 | .15/.05 | .20/.05 | .30/.05 |
| survivor elasticity | 0.0 | +.10 | −.15 | −.30 | −.50 | −.50 | −.50 |
| productivity / price passthrough | .15/.30 | .50/.30 | .30/.50 | .20/.30 | .90/.50 | .90/.50 | .90/.50 |
| demand multiplier | .30 | .30 | .50 | 1.50 | 1.00 | 1.50 | 1.20 |
| baseline growth / interest | .04/.03 | .045/.03 | .04/.03 | .035/.03 | .06/.04 | .08/.04 | .08/.04 |
| state cut share / hike cap | — | — | — | — | .5/.5 | .5/.5 | — |
| automation_tax_rate | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

{{pagebreak}}

# Appendix C — Full fiscal summaries (all years)

The condensed tables in Section 7 omit intermediate years and memo rows; these are complete. The
channel-view decomposition (labour→capital / resident→non-resident / consumer surplus / spending)
is shown for the Windfall comparator.

{{tbl:summary_tax:acemoglu-modest|full|Acemoglu — Modest AI, full fiscal summary ($B).}}

{{tbl:summary_tax:brynjolfsson-augment|full|Brynjolfsson — Augmentation, full fiscal summary ($B).}}

{{tbl:summary_tax:windfall-medium|full|Windfall Trust — Medium, full fiscal summary ($B).}}

{{tbl:summary_channel:windfall-medium|full|Windfall Trust — Medium, four-channel decomposition ($B): labour→capital, resident→non-resident, taxable→consumer-surplus, government spending.}}

{{tbl:summary_tax:china-shock|full|China-Shock Grind, full fiscal summary ($B).}}

{{tbl:summary_tax:agi-20y|full|Korinek–Suh AGI-20y, full fiscal summary ($B).}}

{{tbl:summary_tax:agi-5y|full|Korinek–Suh AGI-5y, full fiscal summary ($B).}}

{{tbl:summary_tax:ai-2027|full|AI 2027 — Fast takeoff, full fiscal summary ($B).}}

{{section:portrait}}
