"""The Korea ScenarioPayload: sanitizer hostility, static ≡ live discipline, the prefix
property the one-run design rests on, and agreement with the bundle's pinned numbers."""
import numpy as np
import pytest

from fiscal_model.korea_cells import PAYM39_CSV

pytestmark = pytest.mark.skipif(
    not PAYM39_CSV.exists(),
    reason="Korea tidy CSV not built — scripts/fetch_korea_tables.py --parse-only")


@pytest.fixture(scope="module")
def pools():
    from fiscal_model.korea_assembly import build_korea_deltas
    return {"data_pool": {}, "deltas": build_korea_deltas(), "ctx_pool": {}}


@pytest.fixture(scope="module")
def central(pools):
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    return build_korea_scenario_payload(sanitize_korea_config({}), **pools)


def test_sanitizer_survives_hostile_bodies():
    from fiscal_model.korea_webpayload import sanitize_korea_config
    cfg = sanitize_korea_config({
        "preset": "agi-5y",                       # US preset key: not a Korea preset → central
        "levers": {"ui_weeks": 400, "mpc": "NaN", "bogus": 9, "adoption_end": -3,
                   "exposure_delta": 0.31, "nhi_share": 2.0,
                   "cognitive_feasibility": 0.0,  # a PINNED convention: must be dropped
                   "demography_path": [1]}})      # structural: must be dropped
    assert cfg["preset"] == "korea-central"
    assert cfg["levers"]["ui_weeks"] == 52                      # clamped, int
    assert cfg["levers"]["adoption_end"] == 0.005               # clamped to floor
    assert cfg["levers"]["exposure_delta"] == 0.5               # snapped to the read grid
    assert cfg["levers"]["nhi_share"] == 0.97                   # clamped to the band
    for k in ("mpc", "bogus", "cognitive_feasibility", "demography_path"):
        assert k not in cfg["levers"]


def test_delisted_levers_are_dropped():
    # interest_rate and survivor_spillover_to_profit left the rail (diplomat review):
    # dead-on-page / inert at rail-reachable configs. Old shared links must not 500.
    from fiscal_model.korea_webpayload import sanitize_korea_config
    cfg = sanitize_korea_config({
        "preset": "korea-central",
        "levers": {"interest_rate": 0.06, "survivor_spillover_to_profit": 0.9}})
    assert cfg["levers"] == {}


def test_reabsorption_exit_pair_cannot_crash(pools):
    # the engine asserts reabsorption + lfp_exit ≤ 1; both levers at their rail maxima
    # must clamp (exit yields), never propagate the AssertionError as a 500
    from fiscal_model.korea_webpayload import (KOREA_LEVER_SPECS,
                                               build_korea_scenario_payload,
                                               sanitize_korea_config)
    hi_reab = KOREA_LEVER_SPECS["reabsorption_rate"][1]
    hi_lfe = KOREA_LEVER_SPECS["lfp_exit_rate"][1]
    p = build_korea_scenario_payload(sanitize_korea_config(
        {"preset": "korea-central",
         "levers": {"reabsorption_rate": hi_reab, "lfp_exit_rate": hi_lfe}}), **pools)
    assert p["final"]["jobs_lost_M"] > 0


def test_default_payload_matches_the_bundle_pins(central):
    f = central["final"]
    assert f["nhi_years_forward"] == pytest.approx(0.50, abs=0.01)
    assert f["nps_given_back"] == pytest.approx(1.14, abs=0.01)
    assert f["ei_shortfall_tn"] == pytest.approx(5.5, abs=0.1)
    assert f["employment_drop_pct"] == pytest.approx(8.95, abs=0.1)
    assert central["config"]["modified_fields"] == []
    assert len(central["rows"]) == 10                           # display horizon, not 40
    assert len(central["funds"]["nps"]["years"]) == 40          # funds get the full window


def test_envelope_contains_central_and_respects_publication(central):
    for key, f in central["funds"].items():
        lo, c, hi = map(np.asarray, (f["eroded_lo"], f["eroded"], f["eroded_hi"]))
        assert (lo <= c + 1e-9).all() and (c <= hi + 1e-9).all(), key
        assert (hi <= np.asarray(f["published"]) + 1e-9).all(), key
    assert central["funds"]["ei"]["years_pulled_forward"] is None   # shortfall story


def test_levers_actually_move_the_payload(pools):
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    p = build_korea_scenario_payload(
        sanitize_korea_config({"levers": {"ui_weeks": 39, "adoption_end": 0.30}}), **pools)
    assert p["config"]["modified_fields"] == ["adoption_end", "ui_weeks"]
    assert p["final"]["ei_shortfall_tn"] > 8.0        # longer window + more adoption
    assert p["final"]["nhi_years_forward"] > 0.60


def test_prefix_property_pins_the_one_run_design(pools):
    """rows sliced from the 40-year run must equal a native 10-year run — if a future
    mechanism reads the horizon (terminal condition, backward pass), this catches it."""
    from fiscal_model.korea_assembly import run_korea_preset
    r10 = run_korea_preset("korea-central", n_periods=10,
                           data=pools["data_pool"][0.0], deltas=pools["deltas"])["res"]
    r40 = run_korea_preset("korea-central", n_periods=40,
                           data=pools["data_pool"][0.0], deltas=pools["deltas"])["res"]
    num = r10.select_dtypes(include=[float, int]).columns
    head = r40.iloc[:10].reset_index(drop=True)
    for c in num:
        assert float((r10[c] - head[c]).abs().max()) < 1e-9, c


def test_agi_preset_payload_matches_its_bundle_row(pools):
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    p = build_korea_scenario_payload(sanitize_korea_config({"preset": "korea-agi-5y"}),
                                     **pools)
    assert p["final"]["nhi_years_forward"] == pytest.approx(2.14, abs=0.02)
    assert p["final"]["ei_shortfall_tn"] == pytest.approx(59.5, abs=0.5)
    assert p["final"]["nps_given_back"] == pytest.approx(7.46, abs=0.05)
    assert p["config"]["display_periods"] == 10


def test_committed_scenario_bundles_match_fresh_generation(pools):
    """Anti-drift: every committed korea/scenarios/<preset>.json must equal what the
    payload function generates today — regenerate with scripts/gen_korea_scenarios.py."""
    import json
    from pathlib import Path

    from fiscal_model.korea_scenarios import KOREA_PRESETS
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    root = Path(__file__).resolve().parent.parent
    for key in KOREA_PRESETS:
        path = root / "web" / "public" / "data" / "korea" / "scenarios" / f"{key}.json"
        assert path.exists(), f"missing bundle for {key} — scripts/gen_korea_scenarios.py"
        committed = json.loads(path.read_text(encoding="utf-8"))
        fresh = json.loads(json.dumps(
            build_korea_scenario_payload(sanitize_korea_config({"preset": key}), **pools)))
        assert fresh == committed, f"stale bundle for {key} — scripts/gen_korea_scenarios.py"


def test_tornado_is_deterministic_and_tracks_the_config(pools):
    from fiscal_model.korea_webpayload import korea_mc_tornado, sanitize_korea_config
    a = korea_mc_tornado(sanitize_korea_config({}), n=50, **pools)
    b = korea_mc_tornado(sanitize_korea_config({}), n=50, **pools)
    assert a == b
    assert set(a["targets"]) == {"nhi_years_forward", "nps_given_back", "ei_shortfall_tn",
                                 "employment_drop_pct", "nhi_erosion_2035"}
    # sampling never reaches the pinned conventions
    for rows in a["targets"].values():
        assert not {r["lever"] for r in rows} & {"cognitive_feasibility",
                                                 "physical_feasibility", "robotics_lag"}
    # a modified config moves the base row the tornado is anchored to
    m = korea_mc_tornado(sanitize_korea_config({"levers": {"ui_weeks": 39}}), n=50, **pools)
    assert m["base"]["ei_shortfall_tn"] > a["base"]["ei_shortfall_tn"] + 1.0


def test_committed_tornado_bundles_match_fresh_generation(pools):
    import json
    from pathlib import Path

    from fiscal_model.korea_webpayload import korea_mc_tornado, sanitize_korea_config
    root = Path(__file__).resolve().parent.parent
    path = root / "web" / "public" / "data" / "korea" / "tornado" / "korea-central.json"
    assert path.exists(), "missing tornado bundle — scripts/gen_korea_scenarios.py"
    committed = json.loads(path.read_text(encoding="utf-8"))
    fresh = json.loads(json.dumps(korea_mc_tornado(
        sanitize_korea_config({"preset": "korea-central"}), n=400, **pools)))
    assert fresh == committed, "stale tornado bundle — scripts/gen_korea_scenarios.py"


def test_policy_levers_route_honestly(pools):
    """The three policy levers, each with its own ledger discipline. vat_pp: calibrated to
    the receipts-measured base, covers >100%/pp-class of the widening, never touches the
    funds. nps_mandate_share: moves the NPS chart/hero, never the treasury. corp_to_funds:
    CONSERVATION — the deficit worsens by exactly what the funds gain, allocated across the
    three funds; even at 100% the funds recover only part of the damage (recapture is
    structurally smaller than contribution erosion — the thesis, quantified)."""
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    base = build_korea_scenario_payload(sanitize_korea_config({}), **pools)

    vat = build_korea_scenario_payload(
        sanitize_korea_config({"levers": {"vat_pp": 1}}), **pools)
    r = vat["policy_readouts"][0]
    assert 7.0 < r["revenue_final_tn"] < 7.92          # 1pp on the ₩792tn base, eroded
    assert r["coverage_pct"] > 100.0
    assert vat["final"]["nhi_years_forward"] == base["final"]["nhi_years_forward"]
    assert vat["final"]["fed_deficit_B"] < base["final"]["fed_deficit_B"]

    man = build_korea_scenario_payload(
        sanitize_korea_config({"levers": {"nps_mandate_share": 0.2}}), **pools)
    assert man["final"]["nps_given_back"] < base["final"]["nps_given_back"]
    assert man["funds"]["nps"]["eroded"][-1] > base["funds"]["nps"]["eroded"][-1]
    assert man["final"]["fed_deficit_B"] == base["final"]["fed_deficit_B"]
    assert man["final"]["nhi_years_forward"] == base["final"]["nhi_years_forward"]

    corp = build_korea_scenario_payload(
        sanitize_korea_config({"levers": {"corp_to_funds": 1.0}}), **pools)
    rc = next(r for r in corp["policy_readouts"] if r["key"] == "corp_to_funds")
    # conservation: reported deficit worsens by exactly the final-year transfer
    assert (corp["final"]["fed_deficit_B"] - base["final"]["fed_deficit_B"]
            ) == pytest.approx(rc["transfer_final_tn"] * 1000.0, abs=5.0)
    # all three funds improve, and none is made MORE than whole
    assert 0 < rc["nps_years_recovered"] < base["final"]["nps_given_back"]
    assert 0 < rc["nhi_years_recovered"] < base["final"]["nhi_years_forward"]
    assert 0 < rc["ei_shortfall_recovered_tn"] < base["final"]["ei_shortfall_tn"]
    # the finding: even 100% recapture transfer does not make the pension whole
    assert corp["final"]["nps_given_back"] > 0.2

    both = build_korea_scenario_payload(sanitize_korea_config(
        {"levers": {"vat_pp": 1, "nps_mandate_share": 0.2, "corp_to_funds": 0.5}}), **pools)
    assert len(both["policy_readouts"]) == 3


def test_legacy_overlay_bodies_map_to_levers(pools):
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    cfg = sanitize_korea_config({"overlays": ["kr-vat", "kr-nps-mandate", "junk"]})
    assert cfg["levers"]["vat_pp"] == 1.0
    assert cfg["levers"]["nps_mandate_share"] == pytest.approx(0.2)
    assert "overlays" not in cfg
    p = build_korea_scenario_payload(cfg, **pools)
    assert {r["key"] for r in p["policy_readouts"]} == {"vat_pp", "nps_mandate_share"}


def test_demography_variants_and_tax_mults(pools):
    """Alex's review asks: the published KOSIS variants move the pension damage in the
    right direction (a shrinking contributor base amplifies the bite), the counterfactual
    property holds under EVERY variant, and the tax mults are ledger-only — they close the
    deficit and never touch the funds."""
    from fiscal_model.korea_webpayload import (build_korea_scenario_payload,
                                               sanitize_korea_config)
    low = build_korea_scenario_payload(sanitize_korea_config(
        {"levers": {"demography_variant": -0.7}}), **pools)      # snaps to -1
    assert low["final"]["demo_variant"] == "low"
    base = build_korea_scenario_payload(sanitize_korea_config({}), **pools)
    high = build_korea_scenario_payload(sanitize_korea_config(
        {"levers": {"demography_variant": 1}}), **pools)
    assert low["final"]["nps_given_back"] > base["final"]["nps_given_back"] \
        > high["final"]["nps_given_back"]
    assert low["final"]["demo_decline_pct"] > high["final"]["demo_decline_pct"]

    # the inert property holds per variant: zero adoption → zero erosion under 저위 too
    from dataclasses import replace as _replace

    from fiscal_model.dynamics_v2 import DynamicModelV2
    from fiscal_model.korea_assembly import korea_erosion_from_run, korea_preset_params
    zp = _replace(korea_preset_params("korea-central", 40, demography_variant="low"),
                  adoption=0.0, adoption_path=[0.0] * 40)
    zm = DynamicModelV2(pools["data_pool"][0.0], pools["deltas"], zp)
    zr = zm.run()
    zb = korea_erosion_from_run(zm, zr, pools["deltas"])
    for scheme, path in zb["erosion"].items():
        assert abs(path).max() < 1e-9, scheme

    m = build_korea_scenario_payload(sanitize_korea_config(
        {"levers": {"corp_tax_mult": 1.2, "income_tax_mult": 0.9}}), **pools)
    assert m["final"]["fed_deficit_B"] != base["final"]["fed_deficit_B"]
    assert m["final"]["nhi_years_forward"] == base["final"]["nhi_years_forward"]
    assert m["final"]["nps_given_back"] == base["final"]["nps_given_back"]
