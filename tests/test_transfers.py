"""Tests for the Part B transfer channel — the baked lookup, fed/state splits, the
two residual phases, and the kernel seam. Skips if the bake hasn't been run."""
from pathlib import Path

import numpy as np
import pytest

LOOKUP = Path(__file__).resolve().parent.parent / "data" / "interim" / "benefit_lookup.parquet"


@pytest.fixture(scope="module")
def lk():
    if not LOOKUP.exists():
        pytest.skip("benefit_lookup not built — run `.venv/bin/python scripts/bake_benefits.py`")
    from fiscal_model.transfers import TransferLookup
    return TransferLookup()


def test_low_wage_displacement_adds_outlays(lk):
    # HoH, 2 kids, TX, $38k household -> $8k after losing a $30k wage
    d = lk.marginal_transfer("Texas", "Head of household", 2, 38_000, 8_000)
    assert d["fed"] > 0 and d["state"] > 0           # SNAP/Medicaid pickup dominates
    assert d["by_program"]["snap"] > 0 and d["by_program"]["medicaid_value"] > 0


def test_medicaid_fed_state_split(lk):
    d = lk.marginal_transfer("Texas", "Head of household", 2, 38_000, 8_000)
    med = d["by_program"]["medicaid_value"]
    # Medicaid is the only large state-share program here -> state ≈ 0.35 * medicaid delta
    assert np.isclose(d["state"], 0.35 * med + 0.5 * d["by_program"]["tanf"], atol=1.0)


def test_high_income_no_means_tested(lk):
    # well above all thresholds in both directions -> ~no SNAP/EITC pickup
    d = lk.marginal_transfer("California", "Married filing jointly", 2, 400_000, 300_000)
    assert abs(d["by_program"]["snap"]) < 1 and abs(d["by_program"]["eitc"]) < 1


def test_ui_benefit_capped(lk):
    assert lk.ui_benefit(30_000, "Texas") == pytest.approx(13_500)       # 0.45 * 30k
    assert lk.ui_benefit(200_000, "Texas") == pytest.approx(20_000)      # capped


def test_two_phases_differ(lk):
    # during-UI vs after-exhaustion give distinct deltas (the EITC hump makes it non-monotonic)
    before, wage = 38_000, 30_000
    after = max(0, before - wage)
    during = after + lk.ui_benefit(wage, "Texas")
    d_after = lk.marginal_transfer("Texas", "Head of household", 2, before, after)
    d_during = lk.marginal_transfer("Texas", "Head of household", 2, before, during)
    assert not np.isclose(d_after["fed"], d_during["fed"])


def test_net_benefits_interpolates(lk):
    nb = lk.net_benefits_by_program("California", "Head of household", 1, 15_000)
    assert nb["eitc"] > 0 and nb["medicaid_value"] > 0


def test_kernel_transfer_seam(lk):
    from fiscal_model import loaders
    from fiscal_model.kernel import Kernel, Worker
    from fiscal_model.transfers import make_transfer_fn
    data = loaders.load_all(validate=False)
    k = Kernel(data)
    k.set_transfer_lookup(make_transfer_fn(lk))
    w = Worker(30_000, 38_000, "Head of household", "Texas", "Retail trade", n_children=2)
    fd = k.fiscal_delta(w, residual_income=0.0)
    assert fd.gained_outlays_fed > 0 and fd.gained_outlays_state > 0
    # transfers now enter the net cost
    assert fd.net_total > 0
