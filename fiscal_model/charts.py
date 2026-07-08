"""Shared altair spec builders — the single source of the fan/tornado/report chart shapes.

Pure functions: no I/O and no theme side effects at import (the print theme is opt-in via
`enable_print_theme()`). Consumed by scripts/monte_carlo.py (HTML export, no extra deps) and
scripts/report_artifacts.py (PNG export via vl-convert, `save_png`). The Streamlit app keeps its
own inline layered fan (dark theme, interactive) — these are the headless/print variants.
"""
from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd

from .mc import PCTS


def fan_widen(percentiles: pd.DataFrame, base_run: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Pivot the long percentile frame to wide (period × p10..p90) and attach the base path."""
    wide = (percentiles.query("metric == @metric")
            .pivot(index="period", columns="pct", values="value").reset_index()
            .rename(columns={p: f"p{p}" for p in PCTS}))
    wide["base"] = base_run[metric].to_numpy()
    return wide


def fan_chart(percentiles: pd.DataFrame, base_run: pd.DataFrame, metric: str,
              y_title: str | None = None, title: str = "",
              width: int = 620, height: int = 330) -> alt.LayerChart:
    """P10–P90 + P25–P75 bands, median line, dashed base path (black — print/HTML variant)."""
    wide = fan_widen(percentiles, base_run, metric)
    return (
        alt.Chart(wide).mark_area(opacity=0.22).encode(
            x=alt.X("period:Q", title="year"), y=alt.Y("p10:Q", title=y_title or metric), y2="p90:Q")
        + alt.Chart(wide).mark_area(opacity=0.35).encode(x="period:Q", y="p25:Q", y2="p75:Q")
        + alt.Chart(wide).mark_line(strokeWidth=2).encode(x="period:Q", y="p50:Q")
        + alt.Chart(wide).mark_line(strokeDash=[6, 3], color="black").encode(x="period:Q", y="base:Q")
    ).properties(width=width, height=height, title=title)


def tornado_chart(tornado: pd.DataFrame, target: str, title: str = "",
                  top: int = 15, width: int = 520) -> alt.Chart:
    """Signed Spearman-ρ bars for the |ρ|-ranked top levers against one final-year target."""
    t = tornado.query("target == @target").head(top)
    return alt.Chart(t).mark_bar().encode(
        x=alt.X("spearman:Q", title=f"Spearman ρ vs {target}"),
        y=alt.Y("lever:N", sort=t["lever"].tolist(), title=None),
    ).properties(width=width, height=24 * len(t) + 20, title=title)


def final_outcome_dotplot(rows: pd.DataFrame, value_title: str = "final-year federal deficit Δ ($B)",
                          width: int = 620) -> alt.LayerChart:
    """Cross-preset comparison: P10–P90 rule + P50 dot per preset.

    `rows` columns: preset (display name), p10, p50, p90."""
    base = alt.Chart(rows).encode(y=alt.Y("preset:N", sort=rows["preset"].tolist(), title=None))
    rule = base.mark_rule(strokeWidth=2).encode(
        x=alt.X("p10:Q", title=value_title), x2="p90:Q")
    dot = base.mark_point(filled=True, size=90).encode(x="p50:Q")
    return (rule + dot).properties(width=width, height=28 * len(rows) + 20)


def overlay_recovery_bars(matrix: pd.DataFrame, width: int = 620) -> alt.Chart:
    """Grouped bars: cumulative deficit recovery ($B) per preset × overlay.

    `matrix` columns: preset (display name), overlay (display name), cum_recovery_B."""
    return alt.Chart(matrix).mark_bar().encode(
        x=alt.X("cum_recovery_B:Q", title="cumulative deficit recovery ($B)"),
        y=alt.Y("overlay:N", title=None),
        row=alt.Row("preset:N", title=None, header=alt.Header(labelAngle=0, labelAlign="left")),
    ).properties(width=width, height=70)


def enable_print_theme() -> None:
    """White-background print theme for headless PNG/HTML export. Opt-in (never at import)."""
    @alt.theme.register("fiscal_report", enable=True)
    def _theme() -> alt.theme.ThemeConfig:
        return {"config": {
            "background": "white",
            "axis": {"labelFontSize": 12, "titleFontSize": 13, "gridColor": "#e6e6e6"},
            "title": {"fontSize": 14, "anchor": "start", "fontWeight": "bold"},
            "legend": {"labelFontSize": 12, "titleFontSize": 12},
            "font": "Helvetica",
        }}


def save_png(chart: alt.Chart, path: Path | str, ppi: int = 200) -> None:
    """Render via vl-convert; ppi stamps physical DPI so Word sizes the figure correctly."""
    chart.save(str(path), ppi=ppi)
