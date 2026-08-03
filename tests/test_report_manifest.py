"""Freshness gate for the report's manifest — the drift firewall needs a firewall of its own.

Report prose cites numbers only through {{n:...}} placeholders resolved against manifest.json, so
prose and model cannot disagree *within* a build. They can still disagree ACROSS builds: edit a
preset, don't rebuild, and the report keeps citing the old model in the new model's name. Two ways
that has actually bitten this repo:

  * ddbf284 shipped a manifest stamped at 202cec6 — built before `adoption_knots` existed — so the
    plan-A/plan-D numbers described a trajectory the code no longer produced.
  * copy round 2 renamed a preset ("China-Shock Grind" -> "Autor et al. — China-shock dynamics")
    without a rebuild, leaving §7.4 naming a scenario the site does not have.

Those are different failures and they cost different amounts to fix, so they are checked
separately: numerics need the ~45-minute rebuild, labels need `--stage render` (~30s).
"""
import json
from pathlib import Path

import pytest

from fiscal_model import app_params, presets

MANIFEST = Path(__file__).resolve().parent.parent / "docs" / "report" / "artifacts" / "manifest.json"


@pytest.fixture(scope="module")
def manifest() -> dict:
    if not MANIFEST.exists():
        pytest.skip(f"{MANIFEST} absent — build it with scripts/report_artifacts.py")
    return json.loads(MANIFEST.read_text())


def test_covers_every_preset(manifest):
    """The report is scoped to all twelve presets; a preset added without a rebuild has no
    numbers, and the docx build would fail loud on its unresolved placeholders."""
    assert set(manifest["presets"]) == set(presets.PRESETS), \
        "manifest preset set != PRESETS — re-run scripts/report_artifacts.py"


def test_numerics_match_source(manifest):
    """Every cached number must have come from the params today's source produces.

    cfg_key is repr-exact over the resolved V2Params, so this catches any change to a lever
    override, an adoption endpoint, the kink year, or the knot trajectory."""
    for key, p in presets.PRESETS.items():
        frag = manifest["presets"].get(key)
        assert frag is not None, f"{key}: absent from the manifest — re-run scripts/report_artifacts.py"
        assert "cfg_key" in frag, (
            f"{key}: manifest predates the cfg_key gate — re-run scripts/report_artifacts.py")
        assert frag["cfg_key"] == app_params.cfg_key(presets.to_params(p)), (
            f"{key}: report numbers are STALE — the preset's params changed since the build. "
            "Re-run scripts/report_artifacts.py (a full rebuild; --stage render will NOT fix this).")


def test_display_labels_match_source(manifest):
    """Names and blurbs reach the docx through the manifest (build_report_docx.py imports no
    fiscal_model), so a rename must not leave the report and the site disagreeing."""
    for key, p in presets.PRESETS.items():
        frag = manifest["presets"].get(key)
        assert frag is not None, f"{key}: absent from the manifest — re-run scripts/report_artifacts.py"
        for field in ("name", "blurb"):
            assert frag.get(field) == getattr(p, field), (
                f"{key}.{field}: report label is stale ({frag.get(field)!r} vs {getattr(p, field)!r})"
                " — re-run scripts/report_artifacts.py --stage render (cheap, no model runs).")


def test_comparison_panels_carry_current_names(manifest):
    """The small-multiple grids bake the display name into a CSV column, so they go stale on a
    rename independently of the manifest."""
    import pandas as pd
    comp = MANIFEST.parent / "comparison"
    expected = {p.name for p in presets.PRESETS.values()}
    for fname in ("fan_grid_panels.csv", "tornado_grid_panels.csv", "final_outcomes.csv"):
        f = comp / fname
        if not f.exists():
            pytest.skip(f"{fname} absent — build the comparison stage")
        assert set(pd.read_csv(f)["preset"]) == expected, \
            f"{fname}: panel labels stale — re-run scripts/report_artifacts.py --stage render"
