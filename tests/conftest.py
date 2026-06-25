import pytest

from fiscal_model import loaders


@pytest.fixture(scope="session")
def data():
    """Load & validate all files once for the whole test session (load is ~4s)."""
    return loaders.load_all(validate=True)


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
