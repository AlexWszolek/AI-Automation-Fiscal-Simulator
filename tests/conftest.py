import pytest

from fiscal_model import loaders


@pytest.fixture(scope="session")
def data():
    """Load & validate all files once for the whole test session (load is ~4s)."""
    return loaders.load_all(validate=True)


@pytest.fixture(scope="session")
def c8_compare():
    """Guarded C8 helper (note E): asserts the config is a v1-reduction, then asserts DynamicModelV2
    reproduces v1 on `cols`. The C8 harness may ONLY be invoked with a reduction config."""
    import numpy as np

    from fiscal_model import levers_v2
    from fiscal_model.dynamics import DynamicModel
    from fiscal_model.dynamics_v2 import DynamicModelV2

    def _cmp(data, deltas, v2p, cols, atol=1e-9):
        assert levers_v2.is_v1_reduction(v2p), "C8 must be run against a v1-reduction config (note E)"
        lp, dp = v2p.to_v1()
        r1 = DynamicModel(data, deltas, lp, dp).run()
        r2 = DynamicModelV2(data, deltas, v2p).run()
        for c in cols:
            assert np.allclose(r1[c].to_numpy(), r2[c].to_numpy(), atol=atol, rtol=0), c
        return r1, r2

    return _cmp


# Several test modules pytest.skip when the (gitignored) build artifacts are absent —
# benefit_lookup.parquet, noc_distribution.csv, the worker-delta cache. On a fresh clone
# that makes the suite report green with hidden skips. Surface that loudly at the end so a
# "passing" run that silently skipped the transfer/integration/dynamics tests is obvious.
_ARTIFACT_HINTS = ("not built", "artifact", "cache", "benefit_lookup", "noc", "bake")


def _skip_reason(report) -> str:
    lr = getattr(report, "longrepr", None)
    if isinstance(lr, tuple) and len(lr) == 3:   # (path, lineno, "Skipped: <msg>")
        return str(lr[2])
    return str(lr or "")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    skipped = terminalreporter.stats.get("skipped", [])
    artifact_skips = [r for r in skipped
                      if any(h in _skip_reason(r).lower() for h in _ARTIFACT_HINTS)]
    if not artifact_skips:
        return
    tr = terminalreporter
    tr.write_sep("=", "MISSING-ARTIFACT SKIPS", yellow=True)
    tr.write_line(f"{len(artifact_skips)} test(s) skipped because build artifacts are absent — "
                  "this run did NOT exercise the transfer/integration/dynamics paths.")
    tr.write_line("Rebuild them (see README 'Setup'), e.g.:")
    tr.write_line("  .venv/bin/python -m fiscal_model.noc")
    tr.write_line("  .venv/bin/python scripts/bake_benefits.py")
    tr.write_line("  .venv/bin/python -m fiscal_model.dynamics   # per-worker delta precompute")
    for r in artifact_skips:
        tr.write_line(f"  - {r.nodeid}")
