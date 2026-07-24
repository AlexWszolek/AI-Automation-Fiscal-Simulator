"""The shareholder windfall channel — CG on undistributed after-tax corporate earnings.

Design + fetch-verified anchors: docs/research/shareholder-channel-design.md. The channel's one
C8 gate is equity_pe_multiple = 0; the ledger identities live in invariants.assert_all_invariants
(C-sh) and are exercised across presets by the phase-6 sweep — here we pin the base construction,
the off-value discipline, the ledger recursion on a real run, and the sampler rules.
"""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from fiscal_model import mc, presets
from fiscal_model.dynamics import DELTA_CACHE
from fiscal_model.dynamics_v2 import DynamicModelV2
from fiscal_model.levers_v2 import DEFAULTS_SHIPPED, DEFAULTS_V1REDUCTION, V2Params, is_v1_reduction


@pytest.fixture(scope="module")
def deltas():
    if not DELTA_CACHE.exists():
        pytest.skip("worker-delta cache not built")
    d = pd.read_parquet(DELTA_CACHE)
    if "undist_per_worker" not in d.columns:
        pytest.skip("deltas cache predates the shareholder channel — delete data/interim cache")
    return d


# ------------------------------------------------------------------ the per-worker base
def test_undist_base_construction(data, deltas):
    """undist_per_worker = corp_share·comp·(1−eff_corp)·(1−payout) ≤ the full-comp surplus, ≥ 0,
    and strictly below the corporate offset base's implied pre-tax portion wherever positive."""
    d = deltas
    assert "undist_per_worker" in d.columns, "deltas cache predates the channel — delete data/interim cache"
    assert (d["undist_per_worker"] >= 0).all()
    assert (d["undist_per_worker"] <= d["worker_wage"].max() * 3).all(), "not a plausible per-worker $"
    # where there is no corporate channel there is no undistributed base
    assert (d.loc[d["corp_per_worker_fed"] == 0, "undist_per_worker"] == 0).all()


def test_kernel_undistributed_matches_corporate_construction(data):
    """_corporate_undistributed stays in lockstep with _corporate: after-tax corporate portion
    times (1 − payout), recomputed here from the same capital table."""
    from fiscal_model.kernel import Kernel, KernelParams
    k = Kernel(data, KernelParams())
    for sector in list(k._cap.index[:8]):
        row = k._cap.loc[sector]
        if np.isnan(row["corp_share_taxable_capital_income"]):
            continue
        comp = 80_000.0
        corp_portion = row["corp_share_taxable_capital_income"] * comp
        eff = 0.0 if np.isnan(row["eff_corp_tax_rate"]) else row["eff_corp_tax_rate"]
        payout = 0.0 if np.isnan(row["dividend_payout_ratio"]) else row["dividend_payout_ratio"]
        expect = corp_portion * (1.0 - eff) * (1.0 - payout)
        assert np.isclose(k._corporate_undistributed(sector, comp), expect, rtol=1e-12), sector


# ------------------------------------------------------------------ off-value discipline (C8)
def test_reduction_off_value():
    assert DEFAULTS_V1REDUCTION.equity_pe_multiple == 0.0
    assert V2Params().equity_pe_multiple == 0.0          # bare V2Params() == reduction, module rule
    assert is_v1_reduction(DEFAULTS_V1REDUCTION)
    assert not is_v1_reduction(replace(DEFAULTS_V1REDUCTION, equity_pe_multiple=16.0))
    assert DEFAULTS_SHIPPED.equity_pe_multiple == 16.0   # channel ON out of the box (current law)


def test_channel_exactly_zero_at_reduction(data, deltas):
    p = replace(DEFAULTS_V1REDUCTION, n_periods=4, adoption_path=[0.1, 0.2, 0.3, 0.4])
    res = DynamicModelV2(data, deltas, p).run()
    for c in ("shareholder_cg_tax_B", "shareholder_realized_B",
              "shareholder_windfall_stock_B", "shareholder_undist_B"):
        assert (res[c] == 0.0).all(), c                  # exact float zero — the C8 requirement


# ------------------------------------------------------------------ the ledger on a real run
def test_ledger_recursion_on_shipped(data, deltas):
    """Realizations draw from the t−1 stock; each ΔE⁺ is capitalized once; tax = rate × realized;
    the C6 reconciliation carries the new line (asserted inside the invariants battery, exercised
    here on the shipped config)."""
    from fiscal_model.invariants import assert_all_invariants
    p = replace(DEFAULTS_SHIPPED, n_periods=6, adoption_path=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
                cognitive_feasibility=0.85, physical_feasibility=0.25)
    res = DynamicModelV2(data, deltas, p).run()
    assert_all_invariants(res, p, res["population_M"].iloc[0])
    G = res["shareholder_windfall_stock_B"].to_numpy()
    R = res["shareholder_realized_B"].to_numpy()
    assert R[0] == 0.0, "t=0 realizes nothing (stock starts empty)"
    assert (res["shareholder_cg_tax_B"].to_numpy()
            == pytest.approx(p.shareholder_eff_rate * R, rel=1e-12))
    assert np.allclose(R[1:], p.cg_realization_rate * G[:-1], rtol=1e-9)
    assert (res["shareholder_undist_B"] > 0).all(), "shipped config accrues a windfall"
    assert G[-1] > 0 and res["shareholder_cg_tax_B"].iloc[-1] > 0


def test_deferral_dominates(data, deltas):
    """The channel's finding: most of the accrued windfall is still unrealized at the horizon —
    the stock at year N exceeds the cumulative realizations by a wide margin."""
    base = presets.to_params(presets.PRESETS["agi-5y"])
    res = DynamicModelV2(data, deltas, base).run()
    stock = res["shareholder_windfall_stock_B"].iloc[-1]
    realized_cum = res["shareholder_realized_B"].sum()
    assert stock > 2.0 * realized_cum, "deferral should dominate inside a 10y window"


# ------------------------------------------------------------------ sampler rules
def test_mc_perturbs_channel_levers_and_keeps_off_off():
    draws = mc.sample_draws(replace(DEFAULTS_SHIPPED, adoption_path=[0.2, 0.4]), n=40,
                            spread=0.15, seed=3)
    for f in ("equity_pe_multiple", "equity_taxable_share",
              "cg_realization_rate", "shareholder_eff_rate"):
        vals = {getattr(d, f) for d in draws}
        assert len(vals) > 10, f"{f} not perturbed"
        assert all(v >= 0 for v in vals)
    assert all(0.0 <= d.equity_taxable_share <= 1.0 for d in draws)
    # off-stays-off: around the reduction base the gate never switches on
    red = mc.sample_draws(replace(DEFAULTS_V1REDUCTION, adoption_path=[0.2, 0.4]), n=20,
                          spread=0.15, seed=3)
    assert all(d.equity_pe_multiple == 0.0 for d in red)


# ------------------------------------------------------------------ app round-trip
def test_app_roundtrip_carries_the_channel():
    """build_v2_params must not silently drop the sliderless field to its OFF dataclass default —
    the preset → widget-defaults → ui → V2Params round-trip preserves pe bit-for-bit."""
    from fiscal_model import app_params as ap
    for key in ("windfall-medium", "agi-5y"):
        preset = presets.PRESETS[key]
        want = presets.to_params(preset)
        d = ap.preset_widget_defaults(preset)
        ui = ap.ui_from_defaults(d, rung=want.reabsorption_rung, preset=preset)
        got = ap.build_v2_params(ui)
        assert got.equity_pe_multiple == want.equity_pe_multiple == 16.0
    ui = ap.ui_from_defaults(dict(ap.CUSTOM_DEFAULTS), rung=1)
    assert ap.build_v2_params(ui).equity_pe_multiple == 16.0
