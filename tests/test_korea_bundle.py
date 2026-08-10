"""The Korea web bundle: the committed korea.json must be exactly what the model generates
(the numerics-match-source pattern), and its internal geometry must be coherent. A red test
here means someone changed the model without regenerating the bundle — run
scripts/gen_korea_bundle.py and re-commit both."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from fiscal_model.korea_cells import PAYM39_CSV

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "web" / "public" / "data" / "korea.json"

pytestmark = pytest.mark.skipif(
    not PAYM39_CSV.exists(),
    reason="Korea tidy CSV not built — scripts/fetch_korea_tables.py --parse-only")


@pytest.fixture(scope="module")
def bundle():
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def test_committed_bundle_matches_a_fresh_generation(tmp_path, bundle):
    spec = importlib.util.spec_from_file_location(
        "gen_korea_bundle", ROOT / "scripts" / "gen_korea_bundle.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gen_korea_bundle"] = mod
    spec.loader.exec_module(mod)
    mod.OUT = tmp_path / "korea.json"
    mod.main()
    fresh = json.loads(mod.OUT.read_text(encoding="utf-8"))
    assert fresh == bundle, "korea.json is stale — regenerate with scripts/gen_korea_bundle.py"


def test_headlines_match_the_integration_pins(bundle):
    """The bundle's headline numbers must agree with the values the integration tests pin —
    one source of truth from model to site."""
    h = bundle["headlines"]
    assert h["nhi"]["published_depletion"] == 2029
    assert h["nps"]["published_depletion"] == 2065
    assert h["nps"]["pre_reform_depletion"] == 2057
    assert h["nps"]["bought_years"] == 8
    assert h["ei"]["planned_2029_tn"] == 21.8
    assert h["nhi"]["years_forward_lo"] <= h["nhi"]["years_forward_central"] \
        <= h["nhi"]["years_forward_hi"]
    assert h["nps"]["given_back_lo"] <= h["nps"]["given_back_central"] \
        <= h["nps"]["given_back_hi"]
    assert h["ei"]["shortfall_lo_tn"] <= h["ei"]["shortfall_central_tn"] \
        <= h["ei"]["shortfall_hi_tn"]


def test_fund_geometry_is_coherent(bundle):
    """Per fund: series lengths agree, the envelope contains the central path, published
    reserves match the model constants, and the band lies at or below published (erosion
    only ever removes revenue)."""
    from fiscal_model.korea_funds import EI_BASELINE, NHI_REFORM, NPS_REFORM
    model = {"nhi": NHI_REFORM, "nps": NPS_REFORM, "ei": EI_BASELINE}
    for key, f in bundle["funds"].items():
        n = len(f["years"])
        assert n == len(f["published"]) == len(f["eroded_central"]) \
            == len(f["eroded_lo"]) == len(f["eroded_hi"])
        lo, c, hi = map(np.asarray, (f["eroded_lo"], f["eroded_central"], f["eroded_hi"]))
        pub = np.asarray(f["published"])
        assert (lo <= c + 1e-9).all() and (c <= hi + 1e-9).all(), key
        assert (hi <= pub + 1e-9).all(), key
        assert f["years"] == list(model[key].years)
        assert f["published"] == pytest.approx(list(model[key].reserves))
        assert f["source"] == model[key].source


def test_composition_block_is_the_seven_institutions(bundle):
    for block in bundle["composition"].values():
        assert len(block) == 7
        assert not any(k.startswith("memo:") for k in block)
    c = bundle["composition"]
    assert c["white_collar_only"]["income tax (national)"] > \
        c["white_collar_only"]["NPS pension"]
    assert c["elementary_only"]["NPS pension"] > \
        c["elementary_only"]["income tax (national)"]
