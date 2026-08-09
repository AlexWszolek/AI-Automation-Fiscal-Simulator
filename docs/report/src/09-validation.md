{{pagebreak}}

# 9. Validation against external models

No other public model computes exactly this object, but three come close enough to triangulate. The
comparisons below run inside the artifact pipeline, with the external targets hard-coded from the
source documents and the model numbers computed fresh on every build. No preset is tuned to hit an
external number, and the disagreements below are displayed rather than closed.

## 9.1 Windfall Trust (Ieong, Saputra, Maniar, and Cheng 2026)

Their simulator computes ten-year total tax revenue changes for an average OECD country under three
displacement scenarios and two value-capture regimes, and their grid replicates on this machinery.
The scenario axis maps to adoption ceilings of 0.20, 0.50, and 0.80 with scarring of 20, 30, and 40
percent; their high-capture allocation, 45 percent firms, 45 percent consumers, and 10 percent
residual, is the Windfall-Medium preset's disposition; and their low-capture allocation of 15, 15,
and 70 maps exactly by routing 70 percent of the saved bill to automation inputs that leak untaxed.
The metric matches theirs: cumulative ten-year total revenue change, federal plus pre-closure state,
as a share of baseline.

{{tbl:windfall_grid|Windfall Trust replication grid: this model vs. their published targets (10-year total revenue change, % of baseline).}}

The comparison validates structure rather than magnitude. The grid reproduces their sign everywhere
and their double monotonicity, worse with more displacement and worse with less value capture, but
at roughly half their magnitudes. The wedge has a known anatomy: their tax base is an average OECD
country, 46 percent labor with a VAT that taxes the consumption their consumer-surplus channel
feeds, while this one is the actual US federal-plus-state system, which is more labor-skewed on the
loss side but carries corporate, compute, and survivor-wage recoveries their static accounting does
not model, and offers only a roughly 2 percent consumption wedge for price declines to escape
through. A model of the US that agreed with a model of the average OECD country would be wrong for
the wrong reasons.

## 9.2 RAND (Price and Suresh 2025)

Their at-cost scenario runs a 10 percentage-point unemployment shock for five years through FRB/US
with AI priced at cost, and finds federal revenue roughly 25 percent lower by 2035, almost entirely
through a 26 percent lower nominal GDP. Replicating that shock here means a one-shot displacement
calibrated to exactly 10 percent of the workforce, using a flat adoption ceiling solved to
{{n:validation.rand_s3.solved_flat_adoption|.3f}}, with reabsorption at 0.2 per year to match their
five-year full return, and all net saving routed to price reductions at full pass-through. The
unemployment proxy starts at {{n:validation.rand_s3.u_proxy_y0_pct|.1f}} percent and falls to
{{n:validation.rand_s3.u_proxy_y5_pct|.1f}} percent by year five.

Federal revenue at year ten is {{n:validation.rand_s3.fed_rev_pct_y10|.1f}} percent below baseline
in this model's own accounting, and {{n:validation.rand_s3.fed_rev_pct_y10_nominal_adj|.1f}} percent
below after scaling revenue unit-elastically by the modeled price level, which sits at
{{n:validation.rand_s3.price_level_y10|.3f}} at year ten, against their −25 percent.

The gap is a mechanism difference and worth stating plainly. RAND's number is overwhelmingly a
deflation result inside a nominal macro model with an active Federal Reserve, while this model never
feeds price-level changes into nominal tax computations, following the A2 rule of Section 4.7,
because real-world bracket schedules are indexed and the double-count risk runs the other way. What
the comparison does confirm is that when prices are allowed to carry revenue the way theirs do,
meaning the adjusted number, the two models' displacement-plus-pricing stories are the same order of
magnitude. The remaining difference is this model's recovery channels, the corporate offset and
reabsorption, which their five-year-recovery scenario also builds in on the employment side but not
on the revenue side.

## 9.3 Acemoglu (2024) and Korinek–Suh (2024)

Two cheap but non-trivial checks. The Acemoglu preset's real-output gain at year ten is
{{n:validation.acemoglu_gdp.y10_gdp_gain_pct|.2f}} percent, inside his roughly 1.1 percent upper
bound, which itself includes capital-deepening effects this model's productivity dividend does not
claim. And the non-AGI presets run on a baseline growth rate consistent with Korinek and Suh's
business-as-usual 2 percent real growth. Neither is a strong test, and both would have caught a
gross mis-calibration, which is the whole of what they are for.

## 9.4 What validation cannot do here

All three external models are themselves models, so none of this is a comparison against the world.
What agreement in sign and ordering across independent architectures does establish is that the
base-migration mechanism is robust to modeling choices, as those architectures are genuinely
different: static accounting in the Windfall case, a DSGE with monetary policy in RAND's, and a
bottom-up cell-level machine here. The magnitudes disagree for identified, mechanical reasons.
Displaying that disagreement is more useful than tuning it away, since a tuned agreement would
conceal exactly the structural differences that make the triangulation informative.
