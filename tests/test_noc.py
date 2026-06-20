"""Tests for the Part A NOC distribution. Runs against the built artifact
(data/interim/noc_distribution.csv); skips if it hasn't been built yet."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

CSV = Path(__file__).resolve().parent.parent / "data" / "interim" / "noc_distribution.csv"


@pytest.fixture(scope="module")
def noc():
    if not CSV.exists():
        pytest.skip("noc_distribution.csv not built — run `python -m fiscal_model.noc`")
    return pd.read_csv(CSV)


def test_shape(noc):
    assert len(noc) == 51 * 3 * 3 * 4  # states x filings x bands x child buckets


def test_probs_sum_to_one_per_cell(noc):
    g = noc.groupby(["filing_status", "state", "income_band_hi"], dropna=False)["prob"].sum()
    assert np.allclose(g.to_numpy(), 1.0, atol=1e-9)


def test_probs_in_range(noc):
    assert noc["prob"].between(0.0, 1.0).all()


def test_single_filers_have_no_children(noc):
    # nonfamily households (-> 'Single') have no own children by definition
    sing = noc[noc["filing_status"] == "Single"]
    zero = sing[sing["n_children"].astype(str) == "0"]
    assert np.allclose(zero["prob"].to_numpy(), 1.0)


def test_hoh_have_children(noc):
    hoh0 = noc[(noc["filing_status"] == "Head of household")
               & (noc["n_children"].astype(str) == "0")]
    assert (hoh0["prob"] < 0.95).all()      # single-parent cells carry real child mass


def test_source_levels_valid(noc):
    assert set(noc["source_level"].unique()) <= {
        "filing_state_band", "filing_state", "filing_national"}
