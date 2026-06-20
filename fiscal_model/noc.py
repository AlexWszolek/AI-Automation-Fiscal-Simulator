"""Part A — NOC (number of own children) distribution from ACS PUMS microdata.

Builds P(children | filing_status, state, income_band) over children in {0,1,2,3+},
WGTP-weighted, with a cell-size fallback ladder. This is the children axis for the
PolicyEngine bake (Part B) and the within-cell integration (Part C). NOT carried at the
occupation level (per-occupation NOC is PUMS sampling noise); occupation enters only via
the income/filing mix the household-archetypes file already provides.

Source: 2024 ACS 1-Year PUMS household file (data/external/pums_hus/psam_hus[ab].csv).
Variables: STATE (FIPS), HHT (household type -> filing proxy), NOC (own children),
HINCP (household income, x ADJINC -> constant $), WGTP (household weight), TYPEHUGQ
(housing-unit filter), NP (persons).

Filing proxy (matches household_archetypes_by_state.xlsx):
    HHT == 1            -> Married filing jointly   (married-couple household)
    HHT in {2, 3}       -> Head of household        (other family, no spouse)
    HHT in {4, 5, 6, 7} -> Single                   (nonfamily household)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PUMS_DIR = Path(__file__).resolve().parent.parent / "data" / "external" / "pums_hus"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "interim"

USECOLS = ["STATE", "HHT", "NOC", "HINCP", "WGTP", "ADJINC", "TYPEHUGQ", "NP"]

# Default income bands (constant 2024 $), tuned to bracket the EITC/Medicaid/SNAP region.
# Fixed (not per-cell tertiles) so Part C can assign a quadrature point to a band globally.
DEFAULT_BAND_EDGES = [-np.inf, 25_000, 55_000, np.inf]

MIN_UNWEIGHTED = 50   # cell-size guard for the fallback ladder

FIPS_TO_STATE = {
    1: "Alabama", 2: "Alaska", 4: "Arizona", 5: "Arkansas", 6: "California",
    8: "Colorado", 9: "Connecticut", 10: "Delaware", 11: "District of Columbia",
    12: "Florida", 13: "Georgia", 15: "Hawaii", 16: "Idaho", 17: "Illinois",
    18: "Indiana", 19: "Iowa", 20: "Kansas", 21: "Kentucky", 22: "Louisiana",
    23: "Maine", 24: "Maryland", 25: "Massachusetts", 26: "Michigan", 27: "Minnesota",
    28: "Mississippi", 29: "Missouri", 30: "Montana", 31: "Nebraska", 32: "Nevada",
    33: "New Hampshire", 34: "New Jersey", 35: "New Mexico", 36: "New York",
    37: "North Carolina", 38: "North Dakota", 39: "Ohio", 40: "Oklahoma", 41: "Oregon",
    42: "Pennsylvania", 44: "Rhode Island", 45: "South Carolina", 46: "South Dakota",
    47: "Tennessee", 48: "Texas", 49: "Utah", 50: "Vermont", 51: "Virginia",
    53: "Washington", 54: "West Virginia", 55: "Wisconsin", 56: "Wyoming",
}

FILING_FROM_HHT = {1: "Married filing jointly",
                   2: "Head of household", 3: "Head of household",
                   4: "Single", 5: "Single", 6: "Single", 7: "Single"}

CHILD_BUCKETS = [0, 1, 2, 3]   # 3 == "3+"


def load_pums_households(pums_dir: Path = PUMS_DIR) -> pd.DataFrame:
    """Load occupied housing-unit records with the variables Part A needs."""
    frames = []
    for name in ("psam_husa.csv", "psam_husb.csv"):
        p = Path(pums_dir) / name
        if not p.exists():
            raise FileNotFoundError(f"PUMS household file not found: {p}")
        frames.append(pd.read_csv(p, usecols=USECOLS))
    df = pd.concat(frames, ignore_index=True)

    # Occupied housing units only: TYPEHUGQ==1 (not group quarters), HHT present, WGTP>0.
    df = df[(df["TYPEHUGQ"] == 1) & df["HHT"].notna() & (df["WGTP"] > 0)].copy()
    df = df[df["HINCP"].notna()]

    df["state"] = df["STATE"].map(FIPS_TO_STATE)
    df = df[df["state"].notna()]                                   # drop territories (none in US file)
    df["filing"] = df["HHT"].astype(int).map(FILING_FROM_HHT)
    df = df[df["filing"].notna()]
    df["hincp_adj"] = df["HINCP"] * df["ADJINC"] / 1_000_000.0     # constant 2024 $
    df["noc_bucket"] = np.minimum(df["NOC"].fillna(0).astype(int), 3)
    df["wgt"] = df["WGTP"].astype(float)
    return df[["state", "filing", "hincp_adj", "noc_bucket", "wgt"]]


def _weighted_dist(g: pd.DataFrame) -> dict:
    """WGTP-weighted P(noc_bucket) over {0,1,2,3+} for a group, normalized to sum 1."""
    w = g.groupby("noc_bucket")["wgt"].sum()
    total = w.sum()
    return {k: (float(w.get(k, 0.0)) / total if total > 0 else 0.0) for k in CHILD_BUCKETS}


def build_noc_distribution(pums_dir: Path = PUMS_DIR,
                           band_edges=DEFAULT_BAND_EDGES,
                           min_unweighted: int = MIN_UNWEIGHTED) -> pd.DataFrame:
    """P(children | filing, state, income_band) with the cell-size fallback ladder."""
    df = load_pums_households(pums_dir)
    band_edges = list(band_edges)
    df["band"] = pd.cut(df["hincp_adj"], bins=band_edges, labels=False, right=False)

    states = sorted(FIPS_TO_STATE.values())
    filings = ["Single", "Head of household", "Married filing jointly"]
    n_bands = len(band_edges) - 1

    # Precompute the three fallback levels.
    dist_fsb = {key: _weighted_dist(g) for key, g in df.groupby(["filing", "state", "band"])}
    dist_fs = {key: _weighted_dist(g) for key, g in df.groupby(["filing", "state"])}
    dist_f = {key: _weighted_dist(g) for key, g in df.groupby("filing")}
    n_fsb = df.groupby(["filing", "state", "band"]).size().to_dict()
    n_fs = df.groupby(["filing", "state"]).size().to_dict()

    rows = []
    for filing in filings:
        for state in states:
            for band in range(n_bands):
                lo, hi = band_edges[band], band_edges[band + 1]
                n1 = n_fsb.get((filing, state, band), 0)
                if n1 >= min_unweighted:
                    dist, src, n_used = dist_fsb[(filing, state, band)], "filing_state_band", n1
                elif n_fs.get((filing, state), 0) >= min_unweighted:
                    dist, src, n_used = dist_fs[(filing, state)], "filing_state", n_fs[(filing, state)]
                else:
                    dist, src, n_used = dist_f[filing], "filing_national", n1
                for k in CHILD_BUCKETS:
                    rows.append({
                        "filing_status": filing, "state": state,
                        "income_band_lo": (np.nan if np.isinf(lo) else lo),
                        "income_band_hi": (np.nan if np.isinf(hi) else hi),
                        "n_children": ("3+" if k == 3 else k),
                        "prob": dist[k], "source_level": src, "n_unweighted": n_used,
                    })
    out = pd.DataFrame(rows)
    return out


def _validate(noc: pd.DataFrame) -> None:
    grp = noc.groupby(["filing_status", "state", "income_band_lo"], dropna=False)["prob"].sum()
    assert np.allclose(grp.to_numpy(), 1.0, atol=1e-9), "NOC probs must sum to 1 within each cell"
    assert noc["prob"].between(0, 1).all()


if __name__ == "__main__":
    import time
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    noc = build_noc_distribution()
    _validate(noc)

    csv_path = OUT_DIR / "noc_distribution.csv"
    noc.to_csv(csv_path, index=False)
    try:
        noc.to_parquet(OUT_DIR / "noc_distribution.parquet", index=False)
        pq = " + parquet"
    except Exception:
        pq = " (parquet skipped: install pyarrow)"

    print(f"built NOC distribution in {time.time() - t0:.1f}s -> {csv_path}{pq}")
    print(f"rows: {len(noc)}  (51 states x 3 filings x 3 bands x 4 child buckets = {51*3*3*4})")
    print("\nsource_level counts (cells):")
    print((noc.groupby('source_level').size() // 4).to_string())

    print("\nNational P(children) by filing (weighted), lowest income band (<$25k):")
    nat = (build_noc_distribution(band_edges=[-np.inf, np.inf])  # single band = overall
           if False else noc)
    show = noc[noc["income_band_hi"] == 25_000].pivot_table(
        index="filing_status", columns="n_children", values="prob", aggfunc="mean")
    print(show.to_string(float_format=lambda x: f"{x:.3f}"))
