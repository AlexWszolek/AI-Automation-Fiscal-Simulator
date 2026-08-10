"""Mutation-testing harness for the Korea modules (run: .venv/bin/python scripts/mutation_korea.py).

Re-run after any substantive Korea change: every mutation must stay killed except the
documented survivor (T6 — bracket-boundary side is value-identical under the 누진공제
construction). A new survivor means a vacuous or missing test. 2026-08-10 baseline: 33/34: apply one deliberate bug at a time, run
the Korea test files, record KILLED (suite went red) vs SURVIVED (suite stayed green)."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TESTS = [
    "tests/test_korea_cells.py", "tests/test_korea_country.py", "tests/test_korea_tax.py",
    "tests/test_korea_transfers.py", "tests/test_korea_demography.py",
    "tests/test_korea_funds.py", "tests/test_korea_scenarios.py",
    "tests/test_korea_exposure.py", "tests/test_korea_integration.py",
]

# (id, file, old, new, note)
MUTATIONS = [
    # ---- korea_tax
    ("T1-bracket-rate", "fiscal_model/korea_tax.py",
     "0.06, 0.15, 0.24", "0.06, 0.16, 0.24", "15% bracket -> 16%"),
    ("T2-prog-deduction", "fiscal_model/korea_tax.py",
     "0.0, 1.26e6, 5.76e6", "0.0, 1.24e6, 5.76e6", "누진공제 typo"),
    ("T3-wsd-ceiling", "fiscal_model/korea_tax.py",
     "_WSD_CEILING = 20_000_000.0", "_WSD_CEILING = 18_000_000.0", "deduction ceiling"),
    ("T4-credit-slope", "fiscal_model/korea_tax.py",
     "715_000.0 + 0.30 *", "715_000.0 + 0.35 *", "credit 30% branch"),
    ("T5-social-dropped", "fiscal_model/korea_tax.py",
     "- BASIC_DEDUCTION - social", "- BASIC_DEDUCTION", "social deduction dropped"),
    ("T6-searchsorted-side", "fiscal_model/korea_tax.py",
     'np.searchsorted(_BRACKET_LO, base, side="right")',
     'np.searchsorted(_BRACKET_LO, base, side="left")',
     "EXPECTED SURVIVOR: boundary assignment value-identical by 누진공제 continuity"),
    # ---- korea_transfers
    ("R1-replacement", "fiscal_model/korea_transfers.py",
     "EI_REPLACEMENT = 0.60", "EI_REPLACEMENT = 0.62", "60% -> 62%"),
    ("R2-floor-factor", "fiscal_model/korea_transfers.py",
     "EI_DAILY_FLOOR = 0.80 *", "EI_DAILY_FLOOR = 0.78 *", "floor 80% -> 78%"),
    ("R3-duration-240", "fiscal_model/korea_transfers.py",
     "120.0, 150.0, 180.0, 210.0, 240.0", "120.0, 150.0, 180.0, 210.0, 239.0", "240d typo"),
    ("R4-tenure-knot", "fiscal_model/korea_transfers.py",
     "0.0, 1.0, 3.0, 5.0, 10.0", "0.0, 1.0, 3.0, 5.0, 9.5", "10yr knot"),
    ("R5-eitc-slope", "fiscal_model/korea_transfers.py",
     "y * (mx / lo)", "y * (mx / mid)", "phase-in slope wrong denominator"),
    ("R6-days-month", "fiscal_model/korea_transfers.py",
     "_DAYS_PER_MONTH = _DAYS_PER_YEAR / 12.0", "_DAYS_PER_MONTH = 30.0", "monthly factor"),
    # ---- korea_funds
    ("F1-no-cumsum", "fiscal_model/korea_funds.py",
     "np.cumsum(lost)", "lost", "erosion not cumulative"),
    ("F2-sign-flip", "fiscal_model/korea_funds.py",
     "np.asarray(fund.reserves[:n]) - np.cumsum", "np.asarray(fund.reserves[:n]) + np.cumsum",
     "shift sign"),
    ("F3-old-date-bug", "fiscal_model/korea_funds.py",
     "return base_year + t + r[t - 1] / (r[t - 1] - r[t])",
     "return base_year + t - 1 + r[t - 1] / (r[t - 1] - r[t])",
     "reintroduce the adversarial-pass off-by-one"),
    ("F4-nhi-revenue", "fiscal_model/korea_funds.py",
     "NHI_REVENUE = (107.6,", "NHI_REVENUE = (106.6,", "revenue transcription typo"),
    ("F5-nhi-reserve", "fiscal_model/korea_funds.py",
     "(25.0, 17.0, 7.6, -1.1,", "(25.0, 17.0, 7.6, 1.1,", "reform 2029 sign"),
    ("F6-nps-knot", "fiscal_model/korea_funds.py",
     "2047: (111.6, 2_895.8),", "2047: (111.6, 2_985.8),", "NPS knot typo"),
    ("F7-interp-frac", "fiscal_model/korea_funds.py",
     "f = (y - lo) / (hi - lo)", "f = (y - lo) / (hi - lo + 1)", "interp denominator"),
    ("F8-memo-share", "fiscal_model/korea_funds.py",
     'KOREA.subnational_transfer_share * out["income tax (national)"]',
     '0.5 * out["income tax (national)"]', "hardcoded passthrough"),
    # ---- korea_cells
    ("C1-midpoint", "fiscal_model/korea_cells.py",
     'cells.loc[closed, "bracket_hi_k"]) / 2.0', 'cells.loc[closed, "bracket_hi_k"]) / 2.1',
     "midpoint divisor"),
    ("C2-annualise", "fiscal_model/korea_cells.py",
     '* 12_000.0', '* 12.0', "annualisation factor"),
    ("C3-bracket-gap", "fiscal_model/korea_cells.py",
     "round(nums[1] + 0.1, 1)", "round(nums[1] + 1.0, 1)", "bracket ceiling"),
    ("C4-solve-denominator", "fiscal_model/korea_cells.py",
     "wsum_closed) / emp_top", "wsum_closed) / (2 * emp_top)", "top-mean solve"),
    # ---- korea_scenarios
    ("S1-reach-dropped", "fiscal_model/korea_scenarios.py",
     'adoption_start=0.01, adoption_end=0.20, n_periods=10, overrides={},\n        adoption_reach_year=9,',
     'adoption_start=0.01, adoption_end=0.20, n_periods=10, overrides={},',
     "reintroduce the reach_year bug on the central preset"),
    ("S2-ei-share", "fiscal_model/korea_scenarios.py",
     "value=189_177 / 203_485", "value=0.95", "wage-linked share hardcoded"),
    ("S3-exposure-ignored", "fiscal_model/korea_scenarios.py",
     "emp * exp_per_cell * a_t", "emp * a_t", "exposure dropped from the chain"),
    ("S4-preset-end", "fiscal_model/korea_scenarios.py",
     "adoption_start=0.01, adoption_end=0.20", "adoption_start=0.01, adoption_end=0.25",
     "central preset end"),
    # ---- korea_exposure
    ("E1-clerical-share", "fiscal_model/korea_exposure.py",
     "3: (0.0, 0.0, 17.4),", "3: (0.0, 0.0, 16.4),", "figure-read value"),
    ("E2-helc-column", "fiscal_model/korea_exposure.py",
     "EXPOSURE_HELC = {g: (v[2] / sum(v) if sum(v) else 0.0) for g, v in FIG9_SHARES.items()}",
     "EXPOSURE_HELC = {g: (v[1] / sum(v) if sum(v) else 0.0) for g, v in FIG9_SHARES.items()}",
     "HELC column swapped for HEHC"),
    # ---- korea_demography
    ("D1-knot-typo", "fiscal_model/korea_demography.py",
     "2030: 34_166,", "2030: 34_266,", "published value typo"),
    ("D2-interp-flip", "fiscal_model/korea_demography.py",
     "frac = (year - lo) / (hi - lo)", "frac = (hi - year) / (hi - lo)", "interp inverted"),
    # ---- rates (Korea payroll)
    ("P1-cap-months", "fiscal_model/rates.py",
     'cap=6_590_000.0 * krw_month', 'cap=6_590_000.0 * 13.0', "13 salary months"),
    ("P2-employee-split", "fiscal_model/rates.py",
     'PayrollComponent("NHI health", "flat", health, health / 2)',
     'PayrollComponent("NHI health", "flat", health, health / 2.1)', "employee split"),
]


def run_tests() -> bool:
    """True = suite green (mutation SURVIVED)."""
    r = subprocess.run(
        [".venv/bin/python", "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider",
         *TESTS],
        cwd=REPO, capture_output=True, text=True, timeout=600)
    return r.returncode == 0


def main():
    results = []
    for mid, fname, old, new, note in MUTATIONS:
        path = REPO / fname
        src = path.read_text()
        if old not in src:
            results.append((mid, "INVALID (pattern not found)", note))
            continue
        if src.count(old) != 1:
            results.append((mid, f"INVALID (pattern x{src.count(old)})", note))
            continue
        try:
            path.write_text(src.replace(old, new, 1))
            survived = run_tests()
            results.append((mid, "SURVIVED" if survived else "killed", note))
        finally:
            subprocess.run(["git", "checkout", "--", fname], cwd=REPO, check=True)
    print(f"\n{'='*74}")
    killed = sum(1 for _, s, _ in results if s == "killed")
    for mid, status, note in results:
        flag = "  " if status == "killed" else "**"
        print(f"{flag}{mid:24s} {status:34s} {note}")
    print(f"{'='*74}\nkilled {killed}/{len(results)}")


if __name__ == "__main__":
    main()
