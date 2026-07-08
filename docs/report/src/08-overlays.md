{{pagebreak}}

# 8. Policy overlays: what government recovers

Each overlay is applied on top of each scenario and re-run; the recovery is the year-by-year
difference in the federal deficit. The table reports the cumulative recovery over each scenario's
horizon, with the share of the scenario's cumulative fiscal gap in parentheses where the gap is
large enough for the ratio to be meaningful.

{{tbl:overlay_recovery|Cumulative federal deficit recovery by scenario × overlay, $B (share of the scenario's cumulative gap in parentheses; omitted where the cumulative gap is below $100B). The UBI column is negative: it is a net cost, shown here for the same accounting frame.}}

Three results.

**Literature-optimal robot taxes are small money.** This is the section's headline and it follows
from an accounting identity, not a modeling choice: the optimal-taxation literature's rates are
ad-valorem on robot *spending* (Costinot–Werning's sufficient statistic tops out at 3.7 percent;
Thuemmel's published estimate is near zero; Guerreiro–Rebelo–Teles is transitional and zero in
steady state), and converting to the saved-wage base multiplies them by `auto_cost`. At
Costinot–Werning's central 2.7 percent the effective rate on saved compensation is 0.3–0.8 percent
across scenarios — recovering single-digit percentages of the fiscal gap everywhere the gap is
large. A robot tax big enough to *replace* the lost labor wedge would need to be an order of
magnitude above anything in the optimal-taxation literature, which that literature rules out
precisely because such a tax would suppress the automation that funds the productivity gains — a
behavioral response this model does not even represent (Section 10), meaning these recovery
numbers are *upper* bounds.

**UBI is a fiscal decision, not a fiscal offset.** At $12,000 per worker with 30 percent
recapture, the UBI's cumulative net cost over the Windfall-Medium decade is
{{n:overlays.windfall-medium.ubi.cum_instrument_B|abs,,.0f}} billion dollars — dwarfing the fiscal
damage of every scenario except the AGI transitions, in which it is comparable to the damage. Its
demand-side effect is real (the level-targeting controller visibly releases induced workers when
the UBI lands) but second-order against its gross cost. In the AGI worlds the interesting number
is different: the required flat tax rate on the *eroded* base to fund it exceeds 100 percent —
UBI in those worlds is only fundable from the capital side, which is Korinek and Lockwood's point.

**Compute parity is the sleeper.** Taxing the compute-capital pool at the domestic-capital ETR
(26.7 percent) instead of the post-TCJA 5 percent recovers the most where automation investment is
heaviest — the fast-takeoff world, where nearly a third of the saved bill flows through the pool.
It is also the overlay with the cleanest incidence story: it taxes the new capital stock that
displacement creates, rather than the act of automation itself.

{{fig:comparison.final_outcome_dotplot|Reprise: the scenario space the overlays operate in. No overlay moves a scenario across the bands separating the modest, grinding, and AGI worlds.}}
