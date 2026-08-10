"""The published exposure vector: the figure read must reconcile with the aggregates the BOK
note states in text, and the within-group fractions must carry the composition facts the
sources describe in prose."""
import pytest

from fiscal_model.korea_exposure import (EXPOSURE_HEHC, EXPOSURE_HELC, FIG9_SHARES)


def test_figure_read_reconciles_with_published_aggregates():
    """The acceptance gate for a figure-derived vector: Σ HEHC ≈ 24%, Σ HELC ≈ 27%,
    everything ≈ 100% — the note's own text numbers."""
    hehc = sum(v[1] for v in FIG9_SHARES.values())
    helc = sum(v[2] for v in FIG9_SHARES.values())
    total = sum(sum(v) for v in FIG9_SHARES.values())
    assert hehc == pytest.approx(24.0, abs=1.0)
    assert helc == pytest.approx(27.0, abs=1.0)
    assert total == pytest.approx(100.0, abs=1.0)


def test_the_composition_facts_match_the_sources_prose():
    """Clerical workers are 'overwhelmingly high-exposure low-complementarity' (BOK) and
    'at risk of displacement' (IMF); professionals are complementarity-heavy; the manual
    groups sit in the low-exposure category (their channel is robotics, not AI-cognitive)."""
    assert EXPOSURE_HELC[3] == 1.0                       # 사무: the displacement epicentre
    assert EXPOSURE_HELC[2] == pytest.approx(4.7 / 21.6)
    assert EXPOSURE_HELC[5] == pytest.approx(3.2 / 9.0)
    assert EXPOSURE_HELC[4] == pytest.approx(1.3 / 12.1)
    for manual in (6, 7, 8, 9):
        assert EXPOSURE_HELC[manual] == 0.0
    assert EXPOSURE_HELC[1] == 0.0                       # managers: high-complementarity
    assert EXPOSURE_HEHC[1] == 1.0
    assert EXPOSURE_HEHC[2] == pytest.approx(16.0 / 21.6)


def test_clerical_is_the_single_biggest_exposed_block():
    """17.4% of ALL Korean employment is clerical AND wholly displacement-prone — the most
    policy-relevant fact the vector carries into the composition results."""
    assert FIG9_SHARES[3] == (0.0, 0.0, 17.4)
    helc_blocks = {g: v[2] for g, v in FIG9_SHARES.items()}
    assert max(helc_blocks, key=helc_blocks.get) == 3


def test_within_group_fractions_partition_each_group():
    """HELC + HEHC + low-exposure fractions must sum to exactly 1 within every populated
    group — the within-group conversion may not leak employment."""
    for g, (le, hehc, helc) in FIG9_SHARES.items():
        total = le + hehc + helc
        assert total > 0.0, g
        le_frac = le / total
        assert EXPOSURE_HELC[g] + EXPOSURE_HEHC[g] + le_frac == pytest.approx(1.0), g
        assert 0.0 <= EXPOSURE_HELC[g] <= 1.0 and 0.0 <= EXPOSURE_HEHC[g] <= 1.0


def test_seam_default_is_a_copy_not_an_alias():
    """Mutating the wired seam dict must not corrupt the source-of-truth constants."""
    from fiscal_model import korea_scenarios
    korea_scenarios.EXPOSURE_BY_OCC[3] = 0.5
    try:
        assert EXPOSURE_HELC[3] == 1.0
    finally:
        korea_scenarios.EXPOSURE_BY_OCC[3] = EXPOSURE_HELC[3]
