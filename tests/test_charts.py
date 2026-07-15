"""Chart-builder gate — spec structure only (no rendering; vl-convert is exercised by the report
build, not the suite)."""
import numpy as np
import pandas as pd

from fiscal_model import charts
from fiscal_model.mc import PCTS


def _fake_mc(n_periods=10, metric="fed_deficit_B"):
    rows = [{"metric": metric, "period": t, "pct": p, "value": 100.0 * t + p}
            for t in range(n_periods) for p in PCTS]
    percentiles = pd.DataFrame(rows)
    base_run = pd.DataFrame({metric: np.linspace(0, 500, n_periods)})
    tornado = pd.DataFrame({"target": ["final_fed_deficit_B"] * 3,
                            "lever": ["a", "b", "c"], "spearman": [0.9, -0.5, 0.1]})
    return percentiles, base_run, tornado


def test_fan_widen_and_chart():
    pct, base, _ = _fake_mc()
    wide = charts.fan_widen(pct, base, "fed_deficit_B")
    assert list(wide.columns) == ["period"] + [f"p{p}" for p in PCTS] + ["base"]
    assert len(wide) == 10 and (wide["p90"] > wide["p10"]).all()
    spec = charts.fan_chart(pct, base, "fed_deficit_B", title="t").to_dict()
    assert len(spec["layer"]) == 4                                    # two bands, median, base line
    assert spec["title"] == "t"


def test_tornado_chart_orders_by_given_frame():
    _, _, tor = _fake_mc()
    spec = charts.tornado_chart(tor, "final_fed_deficit_B", top=2).to_dict()
    assert spec["encoding"]["y"]["sort"] == ["a", "b"]               # |rho| order preserved
    assert "final_fed_deficit_B" in spec["encoding"]["x"]["title"]


def test_dotplot_and_recovery_bars():
    rows = pd.DataFrame({"preset": ["A", "B"], "p10": [1, 2], "p50": [3, 4], "p90": [5, 6]})
    spec = charts.final_outcome_dotplot(rows).to_dict()
    assert len(spec["layer"]) == 2
    m = pd.DataFrame({"preset": ["A"], "overlay": ["o"], "cum_recovery_B": [10.0]})
    spec2 = charts.overlay_recovery_bars(m).to_dict()
    assert spec2["encoding"]["row"]["field"] == "preset"


def test_print_theme_registers_white_background():
    charts.enable_print_theme()
    import altair as alt
    assert alt.theme.active == "fiscal_report"
    cfg = charts.fan_chart(*_fake_mc()[:2], "fed_deficit_B").to_dict()["config"]
    assert cfg["background"] == "white"


def test_state_fips_dict():
    from fiscal_model.charts import US_STATE_FIPS
    assert len(US_STATE_FIPS) == 51
    assert US_STATE_FIPS["District of Columbia"] == 11
    assert len(set(US_STATE_FIPS.values())) == 51            # ids unique
    assert all(1 <= v <= 56 for v in US_STATE_FIPS.values())


def test_state_choropleth_spec():
    import pandas as pd
    from fiscal_model import charts
    df = pd.DataFrame({"state": list(charts.US_STATE_FIPS), "net_B": range(51),
                       "shortfall_B": range(51)})
    ch = charts.state_choropleth(df, "net_B", "Net ($B)",
                                 tooltip=[("net_B", "Net", ",.1f"), ("shortfall_B", "Short", ",.1f")],
                                 neg_color="#4e937a", pos_color="#b3554d")
    spec = ch.to_dict()
    assert spec["projection"]["type"] == "albersUsa"
    lookup = [t for t in spec["transform"] if "lookup" in t][0]
    assert lookup["lookup"] == "id" and lookup["from"]["key"] == "fips"
    assert set(lookup["from"]["fields"]) >= {"state", "net_B", "shortfall_B"}
    assert any("isValid" in str(t.get("filter", "")) for t in spec["transform"])
    dom = spec["encoding"]["color"]["scale"]["domain"]
    assert len(dom) == 3 and dom[0] == -dom[2] and dom[1] == 0   # symmetric diverging
    assert len(spec["encoding"]["tooltip"]) == 3                  # state + 2 fields
