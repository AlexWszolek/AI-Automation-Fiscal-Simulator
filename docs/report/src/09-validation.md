{{pagebreak}}

# 9. Validation against external models

No other public model computes exactly this object, but three come close enough to triangulate.
The comparisons below are run inside the artifact pipeline — the external targets are hard-coded
from the source documents; the model numbers are computed fresh each build. We deliberately do not
tune any preset to hit an external number.

## 9.1 Windfall Trust (Ieong, Saputra, Maniar, and Cheng 2026)

Their simulator computes ten-year total tax revenue changes for an *average OECD country* under
three displacement scenarios and two value-capture regimes. We replicate their grid on our
machinery: the scenario axis maps to adoption ceilings of 0.20/0.50/0.80 with scarring of
20/30/40 percent; their high-capture allocation (45 percent firms / 45 percent consumers /
10 percent residual) is the Windfall-Medium preset's disposition, and their low-capture allocation
(15/15/70) maps exactly by routing 70 percent of the saved bill to automation inputs that leak
untaxed. Our metric matches theirs: cumulative ten-year total (federal plus pre-closure state)
revenue change as a share of baseline.

{{tbl:windfall_grid|Windfall Trust replication grid: this model vs. their published targets (10-year total revenue change, % of baseline).}}

The comparison validates *structure*, not magnitude: our grid reproduces their sign everywhere and
their double monotonicity — worse with more displacement, worse with less value capture — but at
roughly half their magnitudes. The wedge has a known anatomy: their tax base is an average OECD
country (46 percent labor, with a VAT that taxes the consumption their consumer-surplus channel
feeds), while ours is the actual US federal-plus-state system — more labor-skewed on the loss
side, but with corporate, compute, and survivor-wage recoveries their static accounting does not
model, and with only a ~2 percent consumption wedge for prices to escape through. A model of the
US that agreed with a model of the average OECD country would be wrong.

## 9.2 RAND (Price and Suresh 2025)

Their at-cost scenario runs a +10 percentage-point unemployment shock for five years through
FRB/US with AI pricing at cost, and finds federal revenue roughly 25 percent lower by 2035, almost
entirely via a 26 percent lower *nominal* GDP. We replicate the shock: a one-shot displacement
calibrated to exactly 10 percent of the workforce (flat adoption ceiling, solved to
{{n:validation.rand_s3.solved_flat_adoption|.3f}}), reabsorption at 0.2 per year (their five-year
full return — our unemployment proxy starts at
{{n:validation.rand_s3.u_proxy_y0_pct|.1f}} percent and falls to
{{n:validation.rand_s3.u_proxy_y5_pct|.1f}} percent by year five), with all net saving routed to
price reductions at full pass-through.

Our federal revenue at year ten is {{n:validation.rand_s3.fed_rev_pct_y10|.1f}} percent below
baseline in the model's own accounting, and
{{n:validation.rand_s3.fed_rev_pct_y10_nominal_adj|.1f}} percent below after scaling revenue
unit-elastically by our modeled price level ({{n:validation.rand_s3.price_level_y10|.3f}} at year
ten) — against their −25 percent. The gap is a mechanism difference, stated plainly: RAND's number
is overwhelmingly a *deflation* result inside a nominal macro model with an active Federal
Reserve, while this model deliberately never feeds price-level changes into nominal tax
computations (the A2 rule, Section 4.6) because real-world bracket schedules are indexed and the
double-count risk runs the other way. What the comparison does confirm: when we let prices carry
revenue the way theirs do (the adjusted number), the two models' *displacement-plus-pricing*
stories are the same order of magnitude, and the remaining difference is our recovery channels —
corporate offset and reabsorption — which their five-year-recovery scenario also builds in on the
employment side but not the revenue side.

## 9.3 Acemoglu (2024) and Korinek–Suh (2024)

Two cheap but non-trivial checks. The Acemoglu preset's real-output gain at year ten is
{{n:validation.acemoglu_gdp.y10_gdp_gain_pct|.2f}} percent — inside his ~1.1 percent
upper bound (which includes capital-deepening effects our productivity dividend does not claim).
And the non-AGI presets run on a baseline growth rate consistent with Korinek and Suh's
business-as-usual 2 percent real growth. Neither is a strong test; both would have caught a gross
mis-calibration.

## 9.4 What validation cannot do here

All three external models are themselves models. Agreement in sign and ordering across independent
architectures — static accounting (Windfall), a DSGE with monetary policy (RAND), and this
bottom-up cell-level machine — is evidence that the base-migration mechanism is robust to modeling
choices. The magnitudes disagree for identified, mechanical reasons, and we have chosen to display
the disagreement rather than tune it away.
