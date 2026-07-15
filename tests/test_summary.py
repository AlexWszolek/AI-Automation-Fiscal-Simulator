"""Fiscal-summary gate — the presentation layer must reconcile to the ledger it presents."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from fiscal_model import summary
from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.government import RevenueLedger
from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION as R

SCEN = dict(cognitive_feasibility=0.85, physical_feasibility=0.25,
            adoption_path=list(np.linspace(0.1, 0.9, 10)))
LIVE = dict(**SCEN, retained_profit_share=0.6, price_reduction_share=0.2, survivor_gains_share=0.2,
            survivor_raise_ceiling=1.5, survivor_elasticity=-0.15, demand_multiplier=0.5,
            auto_cost=0.10, automation_tax_rate=0.05, ubi_annual=12_000, ubi_recapture_rate=0.25,
            lfp_exit_rate=0.03, attrition_rate=0.025, reabsorption_rate=0.3,
            price_passthrough=0.3, productivity_passthrough=0.3, baseline_growth_rate=0.04,
            robotics_lag=4.0)                                   # every fiscal line non-trivial


@pytest.fixture(scope="module")
def run(data):
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built")
    deltas = pd.read_parquet(DELTA_CACHE)
    res = DynamicModelV2(data, deltas, replace(R, **LIVE)).run()
    return res, RevenueLedger(data)


def _years(df):
    import re
    return [c for c in df.columns if c.startswith("Year ") or re.fullmatch(r"\d{4}", str(c))]


def test_tax_view_reconciles_and_totals(run):
    res, ledger = run
    df = summary.build_fiscal_summary(res, ledger, "tax", "busd")
    y = _years(df)
    # keystone: the net row IS −fed_deficit_B (the C6 identity surfaced as presentation)
    net = df[df["label"] == "Net fiscal impact (federal)"][y].iloc[0].to_numpy()
    assert np.allclose(net, -res["fed_deficit_B"].to_numpy(), rtol=1e-9, atol=1e-6)
    # subtotals == the sum of their group's flow rows
    for group, sub in (("Federal revenue changes", "Δ Federal revenue"),
                       ("Federal outlay changes", "Δ Federal outlays")):
        flows = df[(df["group"] == group) & (df["kind"] == "flow")][y].sum().to_numpy()
        subtotal = df[df["label"] == sub][y].iloc[0].to_numpy()
        assert np.allclose(flows, subtotal, rtol=1e-12)
    # the Total column: flows sum over years; levels report the final year
    flow0 = df[df["kind"] == "flow"].iloc[0]
    assert np.isclose(flow0["Total"], flow0[y].sum())
    lvl = df[df["label"] == "Federal debt (Δ cumulative)"].iloc[0]
    assert np.isclose(lvl["Total"], lvl[y[-1]])


def test_channel_view_reconciles(run):
    res, ledger = run
    df = summary.build_fiscal_summary(res, ledger, "channel", "busd")
    y = _years(df)
    net = df[df["label"] == "Net fiscal impact (federal + state)"][y].iloc[0].to_numpy()
    target = -(res["fed_deficit_B"] + res["state_net_total_B"]).to_numpy()
    assert np.allclose(net, target, rtol=1e-9, atol=1e-6)
    # memo rows exist but are excluded from the net (channels 2 and 3's untaxed magnitudes)
    assert (df["kind"] == "memo").sum() >= 2


def test_pct_cbo_revenue_units(run):
    from fiscal_model.grounding import load_cbo_baseline
    res, ledger = run
    cbo = load_cbo_baseline()
    busd = summary.build_fiscal_summary(res, ledger, "tax", "busd", start_year=2026)
    pct = summary.build_fiscal_summary(res, ledger, "tax", "pct_cbo_revenue", start_year=2026)
    y = _years(busd)
    assert y and y[0] == "2026"                                # calendar columns
    rev = np.array([cbo.revenue(int(c)) for c in y])
    # EVERY non-passthrough row divides by that calendar year's projected federal revenue
    for label in ("Income tax", "State income tax"):
        row_b = busd[busd["label"] == label][y].iloc[0].to_numpy()
        row_p = pct[pct["label"] == label][y].iloc[0].to_numpy()
        assert np.allclose(row_p, row_b / rev * 100.0), label
    # %-GDP passthrough rows are untouched
    g_b = busd[busd["label"] == "Deficit (% of GDP)"][y].iloc[0].to_numpy()
    g_p = pct[pct["label"] == "Deficit (% of GDP)"][y].iloc[0].to_numpy()
    assert np.array_equal(g_b, g_p)
    # Total under % = cumulative flow / cumulative projected revenue (never a sum of percents)
    row_b = busd[busd["label"] == "Income tax"][y].iloc[0].to_numpy()
    tot_p = float(pct[pct["label"] == "Income tax"]["Total"].iloc[0])
    assert np.isclose(tot_p, row_b.sum() / rev.sum() * 100.0)


def test_pct_cbo_extrapolates_past_2036(run):
    res, ledger = run
    pct = summary.build_fiscal_summary(res, ledger, "tax", "pct_cbo_revenue", start_year=2030)
    y = _years(pct)
    assert y[-1] == str(2030 + len(y) - 1) and int(y[-1]) > 2036   # horizon crosses the CBO window
    assert np.isfinite(pct[pct["kind"] == "flow"][y].to_numpy(float)).all()


def test_legacy_year_labels_default(run):
    res, ledger = run
    df = summary.build_fiscal_summary(res, ledger, "tax", "busd")     # no start_year
    assert [c for c in df.columns if c.startswith("Year ")]           # report pipeline contract


def test_sign_convention(run):
    res, ledger = run
    df = summary.build_fiscal_summary(res, ledger, "tax", "busd").set_index("label")
    y = _years(df.reset_index())
    assert (df.loc["Income tax", y].to_numpy() <= 1e-9).all()          # lost revenue is NEGATIVE
    assert (df.loc["Corporate recovery", y].to_numpy() >= -1e-9).all()  # recoveries POSITIVE
    assert (df.loc["UBI (gross)", y].to_numpy() > 0).all()             # outlays positive spending


def test_csv_roundtrip(run):
    res, ledger = run
    df = summary.build_fiscal_summary(res, ledger, "channel", "pct_cbo_revenue", start_year=2026)
    back = pd.read_csv(pd.io.common.BytesIO(summary.to_csv_bytes(df)))
    assert back.shape == df.shape and list(back.columns) == list(df.columns)
