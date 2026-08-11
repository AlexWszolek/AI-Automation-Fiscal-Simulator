"""The Korea V2 assembly: the full engine on Korean data, invariants green in both configs,
with the country seams leaving the US path untouched (the rest of the suite is that proof)."""
from dataclasses import replace

import pytest

from fiscal_model.korea_cells import PAYM39_CSV

pytestmark = pytest.mark.skipif(
    not PAYM39_CSV.exists(),
    reason="Korea tidy CSV not built — scripts/fetch_korea_tables.py --parse-only")


@pytest.fixture(scope="module")
def korea_run():
    from fiscal_model.korea_assembly import build_korea_data, build_korea_deltas
    from fiscal_model.korea_demography import korea_demography_path
    from fiscal_model.korea_scenarios import KOREA_PRESETS
    from fiscal_model.presets import build_adoption_path
    data = build_korea_data()
    deltas = build_korea_deltas()
    korea = dict(adoption=0.20,
                 adoption_path=build_adoption_path(KOREA_PRESETS["korea-central"], 10),
                 cognitive_feasibility=1.0, physical_feasibility=0.0,
                 demography_path=list(korea_demography_path(10)))
    return data, deltas, korea


def _run(korea_run, base):
    from fiscal_model.dynamics_v2 import DynamicModelV2
    data, deltas, korea = korea_run
    params = replace(base, **korea)
    return params, DynamicModelV2(data, deltas, params).run()


def test_reduction_config_invariants_green(korea_run):
    from fiscal_model.invariants import assert_all_invariants
    from fiscal_model.levers_v2 import DEFAULTS_V1REDUCTION
    params, res = _run(korea_run, DEFAULTS_V1REDUCTION)
    assert_all_invariants(res, params, float(res["population_M"].iloc[0]), country="kr")
    assert res["max_cell_resid_M"].max() < 1e-9
    assert res["employment_drop_pct"].iloc[-1] == pytest.approx(8.16, abs=0.1)


def test_shipped_full_dynamics_invariants_green(korea_run):
    """Every dynamic channel live — demand destruction, survivor wages, the UI window, the
    demographic outflow — on Korean data, with the whole battery including per-cell C1."""
    from fiscal_model.invariants import assert_all_invariants
    from fiscal_model.levers_v2 import DEFAULTS_SHIPPED
    params, res = _run(korea_run, DEFAULTS_SHIPPED)
    assert_all_invariants(res, params, float(res["population_M"].iloc[0]), country="kr")
    f = res.iloc[-1]
    assert f["employment_drop_pct"] == pytest.approx(8.95, abs=0.1)
    assert f["induced_M"] > 0.05                    # demand destruction is LIVE
    assert f["W_survivor"] > 1.005                  # survivor wages are LIVE
    assert f["retired_M"] > 1.0                     # the demographic outflow is LIVE
    # the no-closure mirror: Korea reports the local shortfall, never austerity-closes it
    assert (res["state_rate_hike_B"] == 0).all()
    assert (res["state_spending_cut_B"] == 0).all()


def test_korea_refuge_is_the_zero_helc_occupations(korea_run):
    from fiscal_model import reabsorption
    data, _, _ = korea_run
    low = reabsorption.low_exposure_socs(data)
    assert len(low) > 50                            # manual groups' cells populate the refuge
    assert all(code.split(":")[0] in {"1", "6", "7", "8", "9"} for code in low)
