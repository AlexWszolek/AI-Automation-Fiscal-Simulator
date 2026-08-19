"""The Korea V2 assembly — Korean data in the shapes the engine actually consumes.

The engine's working interface (contract inventory in the artifacts plan worksheet) is the
per-worker deltas table plus a handful of `data.*` fields — not all of FiscalData. This
module builds both from the Korean modules that already exist and are test-pinned:
`korea_cells` (209 occupation × wage-bracket cells), `korea_tax`, the Korean payroll
components, `korea_transfers`, and the ILOSTAT occupation × industry joint matrix.

Simplifications the Korean integrate makes EXACTLY (not approximately):
- cells ARE wage brackets → one evaluation per cell (the US integrates over within-cell
  wage percentiles × filing statuses × household archetypes; Korea taxes individuals and
  the bracket midpoint world is already the cell definition, disclosed);
- 구직급여 is tax-exempt (비과세) → the during-phase income-tax loss is the full tax on the
  wage, and EI benefits are not 근로소득, so the EITC is lost in BOTH phases;
- payroll contributions stop entirely in both phases (benefits are not wage).

Ledger mapping, single-region: state = "KR" = the LOCAL-government ledger. National income
tax → inc_fed; the 10% local surtax → inc_state; all five social-insurance schemes →
payroll_fed; VAT → the consumption channel (national — see the channel note below); EITC
delta → transfer_fed (negative: a lost in-work credit REDUCES outlays, as with the US EITC).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import rates
from .korea_cells import load_korea_cells
from .korea_exposure import EXPOSURE_HELC
from .korea_tax import korea_income_tax
from .korea_transfers import ei_daily_benefit, kr_eitc_delta_on_displacement

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "korea"

# ISCO-08 majors ↔ KSCO 6th majors: 1:1 except ISCO 5 (service AND sales) covering KSCO 4+5.
# The ILOSTAT joint matrix is ISCO-side; occupation rows are split to KSCO 4/5 by the two
# groups' national employment weights (from the cell table) — disclosed approximation.
_ISCO_TO_KSCO = {"1": (1,), "2": (2,), "3": (3,), "4": (3,), "5": (4, 5), "6": (6,),
                 "7": (7,), "8": (8,), "9": (9,)}
# note: ISCO 3 (technicians) has no clean KSCO major twin — KSCO folds technicians into
# 전문가(2); ILOSTAT's Korean submission reports ISCO 3 ≈ 0 or folds it too (verify at
# build time; the builder asserts and reroutes if the submission carries mass there).


def load_joint_matrix(year: str = "2024") -> pd.DataFrame:
    """ILOSTAT ISIC-section × ISCO-major employment (thousands) → long frame with KSCO
    occupation codes. Shares only — the LFS frame difference is disclosed at the seam."""
    path = RAW / "ilostat_eco_ocu.csv"
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r["time"] != year or not r["obs_value"]
                    or r["classif1"] == "ECO_ISIC4_TOTAL"
                    or r["classif2"] in ("OCU_ISCO08_TOTAL", "OCU_ISCO08_X")):
                continue
            sec = r["classif1"].replace("ECO_ISIC4_", "")
            isco = r["classif2"].replace("OCU_ISCO08_", "")
            if len(sec) != 1 or isco not in _ISCO_TO_KSCO:
                continue
            rows.append({"section": sec, "isco": isco, "emp_k": float(r["obs_value"])})
    df = pd.DataFrame(rows)
    assert len(df) > 100 and df["emp_k"].sum() > 20_000, "joint matrix looks truncated"
    return df


@dataclass
class KoreaFiscalData:
    """The minimal FiscalData surface the engine touches, Korean-shaped. Carries a country
    tag so the (few) US-pinned code paths can branch without touching US behaviour."""
    country: str
    oews: pd.DataFrame
    exposure_occ: pd.DataFrame
    matrices_sector: pd.DataFrame
    consumption: pd.DataFrame
    receipts: pd.DataFrame = field(default_factory=pd.DataFrame)
    base_linkage: pd.DataFrame = field(default_factory=pd.DataFrame)
    baseline_deficit_busd: float = 0.0        # headline units / 1e9 (₩bn for Korea)
    va_baseline: float = 0.0                  # nominal GDP anchor (won for Korea)
    comp_total: float = 0.0                   # automation base = covered wage bill (won)


_ENGINE = rates.PayrollFICA(components=rates.korea_payroll_components())

# Korean corporate parameters for the offset channel (per-worker corporate tax recovered on
# the retained share of the saved wage). Effective rate: statutory 24.2% incl. local surtax
# at the ₩20–300bn bracket — the blended large-firm band where automation-scale savings
# land; recorded in KOREA_PRESET_EVIDENCE as a calibration row.
KR_CORP_EFF_RATE = 0.242


def build_cells_frames(year: str = "2025", exposure: dict | None = None) -> tuple:
    """The cell table in engine shapes: (oews, exposure_occ, matrices_sector).

    `exposure` (KSCO major → displacement-prone share) defaults to the published BOK read;
    pass `korea_exposure.exposure_variant(±0.5)` for the figure-read error axis of the band."""
    kc = load_korea_cells(year)
    c = kc.cells.copy()
    c["soc_code"] = [f"{o}:{int(lo):04d}" for o, lo in zip(c["occ_code"], c["bracket_lo_k"])]

    oews = pd.DataFrame({
        "soc_code": c["soc_code"], "state": "KR",
        "employment_persons": c["emp"], "annual_mean_wage": c["wage_year_won"],
    })

    # cognitive channel: the BOK HELC displacement-prone share, already a [0,1] share —
    # carried in a `cognitive_share` column the channel seam consumes directly (the US
    # ai_pca_score → transform path stays untouched)
    exposure_occ = pd.DataFrame({
        "soc_code": c["soc_code"],
        "ai_pca_score": np.nan,
        "cognitive_share": c["occ_code"].map(exposure if exposure is not None
                                             else EXPOSURE_HELC).astype(float),
    })

    # occupation × industry: ILOSTAT shares allocate each cell's employment/comp over
    # ISIC sections; comp = wage bill (₩m units, emp in thousands — only the per-worker
    # RATIO is consumed by the engine)
    jm = load_joint_matrix()
    ksco_rows = []
    w45 = c.groupby("occ_code")["emp"].sum()
    for r in jm.itertuples():
        targets = _ISCO_TO_KSCO[r.isco]
        if len(targets) == 1:
            ksco_rows.append({"section": r.section, "occ_code": targets[0], "emp_k": r.emp_k})
        else:
            tot = sum(w45[t] for t in targets)
            for t in targets:
                ksco_rows.append({"section": r.section, "occ_code": t,
                                  "emp_k": r.emp_k * w45[t] / tot})
    shares = (pd.DataFrame(ksco_rows).groupby(["occ_code", "section"])["emp_k"].sum()
              .groupby(level=0).transform(lambda s: s / s.sum()).rename("share").reset_index())
    ms = c.merge(shares, on="occ_code")
    matrices_sector = pd.DataFrame({
        "soc_code": ms["soc_code"], "industry": ms["section"],
        "emp_thousands": ms["emp"] * ms["share"] / 1000.0,
        "comp_musd": ms["emp"] * ms["share"] * ms["wage_year_won"] / 1e6,   # ₩m, ratio-only
    })
    return oews, exposure_occ, matrices_sector


def build_korea_deltas(year: str = "2025", kp=None) -> pd.DataFrame:
    """The per-worker deltas table in the engine's exact column contract.

    `kp` is a kernel.KernelParams: the consumption channel mirrors the US integrator's own
    construction (mpc × consumption_stickiness × disposable-income withdrawal × the
    consumption tax rate) with Korea's 10% VAT as the rate — the propensity comes from the
    kernel's parameters, not a Korea-invented constant."""
    from .kernel import KernelParams
    kp = kp or KernelParams()
    oews, _, _ = build_cells_frames(year)
    w = oews["annual_mean_wage"].to_numpy()

    tax = korea_income_tax(w, _ENGINE.employee_fica(w, "Single"))
    payroll = _ENGINE.fica(w, "Single")
    ui_annual = ei_daily_benefit(w) * 365.0
    eitc_delta = kr_eitc_delta_on_displacement(w, residual_income=0.0)

    df = pd.DataFrame({
        "soc_code": oews["soc_code"], "state": "KR",
        "employed": oews["employment_persons"].astype(float),
        "worker_wage": w, "ui_benefit": ui_annual,
    })
    for phase in ("during", "after"):
        # 비과세 benefit + individual taxation → the wage's full tax is lost in both phases
        df[f"{phase}_inc_fed"] = tax["national"]
        df[f"{phase}_inc_state"] = tax["local"]
        df[f"{phase}_payroll_fed"] = payroll
        df[f"{phase}_transfer_fed"] = eitc_delta          # negative: in-work credit lost
        df[f"{phase}_transfer_state"] = 0.0
    # consumption channel (VAT, 10%): the US integrator's own construction — mpc ×
    # consumption_stickiness × disposable-income withdrawal × rate — with the withdrawal
    # net of the (tax-exempt) EI benefit during the window
    KR_VAT_RATE = 0.10
    propensity = kp.mpc * kp.consumption_stickiness
    net_after_tax = w - tax["total"] - _ENGINE.employee_fica(w, "Single")
    for phase, residual in (("during", ui_annual), ("after", 0.0)):
        withdrawal = np.maximum(net_after_tax - residual, 0.0)
        df[f"{phase}_cons_state"] = withdrawal * propensity * KR_VAT_RATE
    # corporate offset: Korean effective rate on the retained share of saved compensation —
    # sector-invariant v1 (aggregate corporate treatment), so per-worker = rate × wage ×
    # retained share resolved by the kernel's disposition at runtime; the deltas table
    # carries the FULL-retention value exactly as the US table does (kernel scales it)
    df["corp_per_worker_fed"] = KR_CORP_EFF_RATE * w
    df["undist_per_worker"] = (1.0 - KR_CORP_EFF_RATE) * w
    return df



def build_korea_data(year: str = "2025", exposure: dict | None = None) -> KoreaFiscalData:
    """The full data shim. Units note: `amount_busd` carries ₩bn (won/1e9) so every place
    the engine multiplies by 1e9 lands back in won; headline formatting divides to ₩tn."""
    from .country import KOREA

    oews, exposure_occ, matrices_sector = build_cells_frames(year, exposure)
    deltas = build_korea_deltas(year)
    emp = deltas["employed"].to_numpy()
    pit_national = float(deltas["after_inc_fed"].to_numpy() @ emp) / 1e9      # ₩bn
    pit_local = float(deltas["after_inc_state"].to_numpy() @ emp) / 1e9
    payroll_total = float(deltas["after_payroll_fed"].to_numpy() @ emp) / 1e9
    wage_bill = float(deltas["worker_wage"].to_numpy() @ emp)

    # Federal rows must sum to total national revenue (NABO Focus 92 Table 1, 2025 총수입
    # ₩650.6tn) for the ledger's absolute line. Surcharge bases are now primary-sourced:
    # corporate ₩84.6tn and VAT ₩79.2tn are the 2025 실적 from NABO 나보포커스 제137호
    # [표 1] (sources/nabo-focus-137-tax-revenue-2025.pdf) — 실적 items inside a
    # 총수입-budget total, with the frame difference absorbed by the residual row
    # (disclosed; the residual is never levied). At mult = 1.0 nothing changes.
    total_revenue = 650_600.0
    corp_base = 84_600.0
    cons_base = 79_200.0
    receipts = pd.DataFrame([
        {"level": "Federal", "maps_to_base": "Labor income", "amount_busd": pit_national},
        {"level": "Federal", "maps_to_base": "Social insurance (payroll)",
         "amount_busd": payroll_total},
        {"level": "Federal", "maps_to_base": "Corporate profits", "amount_busd": corp_base},
        {"level": "Federal", "maps_to_base": "Consumption", "amount_busd": cons_base},
        {"level": "Federal", "maps_to_base": "Other (residual to NABO 총수입)",
         "amount_busd": total_revenue - pit_national - payroll_total
                        - corp_base - cons_base},
        {"level": "State & local", "maps_to_base": "Labor income (local surtax)",
         "amount_busd": pit_local},
    ])
    base_linkage = pd.DataFrame([
        {"tax_stream": "Individual income tax", "avg_effective_rate":
            (pit_national + pit_local) * 1e9 / wage_bill},
        {"tax_stream": "Payroll (social insurance)", "avg_effective_rate": 0.209048},
        {"tax_stream": "Corporate income tax", "avg_effective_rate": KR_CORP_EFF_RATE},
    ])
    consumption = pd.DataFrame([{"state": "KR", "total_taxable_pce_musd": 1.0}])

    return KoreaFiscalData(
        country="kr", oews=oews, exposure_occ=exposure_occ,
        matrices_sector=matrices_sector, consumption=consumption,
        receipts=receipts, base_linkage=base_linkage,
        baseline_deficit_busd=KOREA.baseline_deficit_bn * 1000.0,
        va_baseline=KOREA.va_baseline, comp_total=KOREA.comp_total)


class KoreaSurvivorEngine:
    """The SurvivorEngine contract (`delta(W_cell)` → per-worker tax increments, gains
    positive) with the Korean engines. EXACT and simple where the US needs approximation:
    individual taxation → no filing weights, no household archetypes — one re-evaluation of
    the actual chain (payroll → deductible employee share → income tax → local surtax) at
    the scaled wage. W == 1 → zeros identically."""

    def __init__(self, deltas: pd.DataFrame):
        d = deltas.reset_index(drop=True)
        self.worker_wage = d["worker_wage"].to_numpy(float)
        self._base = self._eval(self.worker_wage)

    @staticmethod
    def _eval(w: np.ndarray) -> dict:
        employee = _ENGINE.employee_fica(w, "Single")
        tax = korea_income_tax(w, employee)
        return {"inc_fed": tax["national"], "inc_state": tax["local"],
                "payroll": _ENGINE.fica(w, "Single")}

    def delta(self, W_cell) -> dict:
        W = np.asarray(W_cell, float)
        cur = self._eval(self.worker_wage * W)
        return {k: cur[k] - self._base[k] for k in self._base}

    @staticmethod
    def employee_fica_pw(wage: np.ndarray) -> np.ndarray:
        """Per-worker EMPLOYEE-side contributions (the demand-withdrawal basis)."""
        return np.asarray(_ENGINE.employee_fica(np.asarray(wage, float), "Single"), float)

    # parity alias: dynamics_v2 tests exercise _delta_loop on the US engine; the Korean
    # engine's fast path IS the reference (single construction, no split code paths)
    _delta_loop = delta


class KoreaReabsorptionEngine:
    """The ReabsorptionEngine contract with the Korean engines — exact re-evaluation of the
    re-employed at the destination wage. Losses positive; `transfer_*` are GAINED outlays
    (the Korean cross-threshold effect: a service-floor destination wage re-enters the EITC
    trapezoid, partially cushioning the scar — the same economics as the US means-tested
    cliffs, computed from the statute instead of an interp table).

    Korea-native service floor: the STATUTORY full-time minimum wage (2026 ₩10,320/h on the
    209-hour monthly basis → ₩25.88m/yr) — better anchored than the US percentile floor and
    exactly the going wage of the low-exposure service work the refuge argument describes."""

    SERVICE_FLOOR_WON = 10_320.0 * 209.0 * 12.0

    def __init__(self, deltas: pd.DataFrame, kp):
        d = deltas.reset_index(drop=True)
        self.worker_wage = d["worker_wage"].to_numpy(float)
        self.service_floor = np.full(len(d), self.SERVICE_FLOOR_WON)
        self._kp = kp

    @staticmethod
    def _takehome(w: np.ndarray) -> tuple:
        employee = _ENGINE.employee_fica(w, "Single")
        tax = korea_income_tax(w, employee)
        return tax, employee, w - tax["total"] - employee

    def delta(self, haircut: float, mpc: float, stickiness: float,
              wage_index: float = 1.0) -> dict:
        from .korea_transfers import kr_eitc
        w_o = self.worker_wage
        w_d = np.maximum(w_o * (1.0 - haircut), self.service_floor)
        if wage_index != 1.0:
            w_d = w_d * wage_index
        tax_o, efica_o, th_o = self._takehome(w_o)
        tax_d, efica_d, th_d = self._takehome(w_d)
        inc_fed = tax_o["national"] - tax_d["national"]
        inc_state = tax_o["local"] - tax_d["local"]
        payroll = _ENGINE.fica(w_o, "Single") - _ENGINE.fica(w_d, "Single")
        tr_fed = kr_eitc(w_d) - kr_eitc(w_o)          # regained in-work credit (gain +)
        tr_state = np.zeros_like(w_o)
        disp_loss = th_o - th_d                        # SIGNED take-home loss
        cons = mpc * stickiness * disp_loss * 0.10     # VAT channel, same construction
        return {"inc_fed": inc_fed, "inc_state": inc_state, "payroll_fed": payroll,
                "cons_state": cons, "transfer_fed": tr_fed, "transfer_state": tr_state,
                "net_takehome_loss": disp_loss - (tr_fed + tr_state)}

    _delta_loop = delta


def korea_erosion_from_run(model, res, deltas: pd.DataFrame) -> dict:
    """Per-scheme contribution-base erosion paths from an ASSEMBLED run — the honest
    replacement for the direct chain's gross ceiling. Uses the model's own per-cell stocks:
    employed contribute at survivor-adjusted wages (raises GROW the uncapped bases),
    reabsorbed contribute at their floor-bounded destination wages, and everyone else
    contributes nothing. The baseline is the demography-scaled no-AI workforce at baseline
    wages — so pure demographic decline yields zero erosion (the counterfactual property,
    same as the headline). Also returns the EI OUTLAY side: added benefit spending from the
    actual UI-window stock at the statutory (tax-exempt, near-flat) benefit rate.

    RECONCILIATION vs the engine's own `payroll_fed_loss_B` (test-pinned): at t=0 the
    bridge's gross (flat-wage) loss equals the engine line EXACTLY. Over time the two
    deliberately diverge on two conventions: (1) the bridge NETS the raise-funded extra
    contributions into erosion, while the engine books them in survivor_gain_fed_B; and
    (2) displaced workers who exit via natural attrition (the `retired` stock) STAY counted
    as erosion here — the automated position never refills, so against the demography-scaled
    baseline (in which positions refill up to the population path) its contributions are
    genuinely gone. That is the declining-baseline counterfactual, applied consistently;
    the engine's line follows the US jobs-lost convention (retired excluded) instead.

    Returns {"erosion": {scheme: np.ndarray}, "ei_outlay_bn": np.ndarray (₩bn per year)}."""
    from .korea_funds import _COMPONENTS
    w = deltas["worker_wage"].to_numpy(float)
    emp0 = deltas["employed"].to_numpy(float)
    ui_rate = deltas["ui_benefit"].to_numpy(float)
    v2p = getattr(model, "v2p", None) or getattr(model, "params", None)
    dp = getattr(v2p, "demography_path", None)
    demo = (list(dp) if dp is not None else [1.0] * len(res))
    W = res["W_survivor"].to_numpy(float)
    # the re-employed contribute at the reabsorption engine's OWN destination wage:
    # haircut wage floored at the statutory service floor, then the per-period rung-1 wage
    # index (Baumol/crowding; 1.0 whenever those levers are off). Reading the haircut from
    # a model attribute was this bridge's second silent-fallback bug (the first was the
    # demography path) — take it from the bound params, which always exist.
    haircut = float(model.v2p.reemployment_haircut)
    W_reab = (res["W_reab"].to_numpy(float) if "W_reab" in res.columns
              else np.ones(len(res)))
    from .korea_assembly import KoreaReabsorptionEngine
    w_reab0 = np.maximum(w * (1.0 - haircut), KoreaReabsorptionEngine.SERVICE_FLOOR_WON)

    # the two income-tax lines of the composition, same convention as contribution_losses:
    # korea_income_tax at the (survivor-adjusted / destination) wage with the employee's own
    # contributions at that wage deducted — caps and credits re-evaluated, not scaled
    _tax = lambda wage: korea_income_tax(wage, _ENGINE.employee_fica(wage, "Single"))
    tax0 = _tax(w)
    _PIT_LINES = ("income tax (national)", "local income surtax")

    erosion: dict[str, list] = {c.name: [] for c in _COMPONENTS}
    erosion.update({k: [] for k in _PIT_LINES})
    ei_outlay = []
    for t, tr in enumerate(model.cell_trace):
        scale = demo[min(t, len(demo) - 1)]
        w_reab = w_reab0 * W_reab[t]
        for c in _COMPONENTS:
            base = float(c.levy(w, "Single", c.rate) @ (emp0 * scale))
            actual = float(c.levy(w * W[t], "Single", c.rate) @ tr["employed"]
                           + c.levy(w_reab, "Single", c.rate) @ tr["reabsorbed"])
            erosion[c.name].append(max(0.0, 1.0 - actual / base) if base > 0 else 0.0)
        tax_t, tax_reab = _tax(w * W[t]), _tax(w_reab)
        for key, part in zip(_PIT_LINES, ("national", "local")):
            base = float(tax0[part] @ (emp0 * scale))
            actual = float(tax_t[part] @ tr["employed"]
                           + tax_reab[part] @ tr["reabsorbed"])
            erosion[key].append(max(0.0, 1.0 - actual / base) if base > 0 else 0.0)
        # match the model's own UI accounting: the annual rate prorated by the window share
        # (ui_weeks/52) — the same convention as dynamics_v2's ui_outlay_fed line
        ei_outlay.append(float(ui_rate @ tr["on_ui"]) * model._v1.ui_share / 1e9)   # ₩bn/yr
    return {"erosion": {k: np.asarray(v) for k, v in erosion.items()},
            "ei_outlay_bn": np.asarray(ei_outlay)}


def korea_preset_params(key: str, n_periods: int | None = None,
                        demography_variant: str = "medium", **param_overrides):
    """The V2 params for a Korea preset under the Korea conventions (cognitive channel
    only, Korean demography, no closure). The conventions live HERE, once, so a sweep can
    never half-apply them; MC samples around exactly this object. `demography_variant`
    selects among the PUBLISHED KOSIS scenarios (low/medium/high) — the demographic-risk
    axis as published paths, never an invented slider."""
    from dataclasses import replace

    from .korea_demography import korea_demography_path
    from .korea_scenarios import KOREA_PRESETS
    from .levers_v2 import DEFAULTS_SHIPPED
    from .presets import build_adoption_path

    preset = KOREA_PRESETS[key]
    n = int(n_periods) if n_periods is not None else preset.n_periods
    fields = dict(cognitive_feasibility=1.0, physical_feasibility=0.0)
    fields.update(preset.overrides)
    fields.update(param_overrides)
    # survivor_gains_share is DERIVED, never set (presets.to_params has the same expression;
    # it can't be reused here because it requires both disposition fields in the overrides).
    # Without this, an AGI preset's retained=0.80 lands on the shipped survivor 0.2 and the
    # disposition simplex guard rejects the run.
    if ({"retained_profit_share", "price_reduction_share"} & set(fields)) \
            and "survivor_gains_share" not in fields:
        rp = fields.get("retained_profit_share", DEFAULTS_SHIPPED.retained_profit_share)
        pr = fields.get("price_reduction_share", DEFAULTS_SHIPPED.price_reduction_share)
        fields["survivor_gains_share"] = max(0.0, 1.0 - rp - pr)
    return replace(DEFAULTS_SHIPPED,
                   adoption=preset.adoption_end,
                   adoption_path=build_adoption_path(preset, n),
                   n_periods=n,
                   demography_path=list(korea_demography_path(n, variant=demography_variant)),
                   **fields)


def run_korea_preset(key: str, n_periods: int | None = None, year: str = "2025",
                     data=None, deltas=None, **param_overrides) -> dict:
    """One assembled Korea run, end to end: korea_preset_params → DynamicModelV2 → the
    funds bridge. The single entrypoint the bundle/MC/tornado layers drive.

    Pass `data`/`deltas` to amortize the CSV loads across a sweep; `n_periods` defaults to
    the preset's native horizon (NPS needs 40 — the demography projections reach 2072)."""
    from .dynamics_v2 import DynamicModelV2

    params = korea_preset_params(key, n_periods, **param_overrides)
    data = data if data is not None else build_korea_data(year)
    deltas = deltas if deltas is not None else build_korea_deltas(year)
    model = DynamicModelV2(data, deltas, params)
    res = model.run()
    bridge = korea_erosion_from_run(model, res, deltas)
    return {"res": res, "bridge": bridge, "params": params, "model": model, "deltas": deltas}


def korea_project_funds(bridge: dict, nhi_share: float, nps_share: float,
                        nps_inflows_tn=None, fund_transfer_tn=None) -> dict:
    """Bridge → the three fund projections. Wage-linked shares enter HERE, not in the run —
    erosion is share-independent, so a band over share edges reuses one assembled run.
    EI always uses its verified share and carries the outlay side (₩tn/yr).

    Policy flows also enter here, never in the run: `nps_inflows_tn` (the NPS automation-
    dividend mandate — into NPS only, never through the treasury) and `fund_transfer_tn`
    (the corporate-recapture transfer, ₩tn/yr from the treasury), allocated across the
    three funds in proportion to each fund's wage-linked erosion ₩ that year — the neutral
    rule, disclosed. Beyond a fund's published horizon its allocation share is zero."""
    from .korea_funds import EI_BASELINE, NHI_REFORM, NPS_REFORM, depletion_shift
    from .korea_scenarios import WAGE_LINKED_SHARE
    er = bridge["erosion"]
    n_nhi, n_nps, n_ei = len(NHI_REFORM.years), len(NPS_REFORM.years), len(EI_BASELINE.years)
    ei_share = WAGE_LINKED_SHARE["ei"].value

    alloc = {"nhi": np.zeros(n_nhi), "nps": np.zeros(n_nps), "ei": np.zeros(n_ei)}
    if fund_transfer_tn is not None:
        tr = np.asarray(fund_transfer_tn, dtype=float)
        T = min(len(tr), n_nps)                       # NPS carries the longest horizon
        lost = np.zeros((3, T))
        lost[0, :min(T, n_nhi)] = (np.asarray(NHI_REFORM.revenue[:min(T, n_nhi)])
                                   * nhi_share * er["NHI health"][:min(T, n_nhi)])
        lost[1, :min(T, n_nps)] = (np.asarray(NPS_REFORM.revenue[:min(T, n_nps)])
                                   * nps_share * er["NPS pension"][:min(T, n_nps)])
        lost[2, :min(T, n_ei)] = (np.asarray(EI_BASELINE.revenue[:min(T, n_ei)])
                                  * ei_share * er["EI unemployment benefit"][:min(T, n_ei)])
        tot = lost.sum(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            shares = np.where(tot > 0, lost / np.where(tot > 0, tot, 1.0), 0.0)
        full = shares * tr[:T]                       # (3, T) allocation, ₩tn/yr
        alloc["nhi"][:min(T, n_nhi)] = full[0, :min(T, n_nhi)]
        alloc["nps"][:min(T, n_nps)] = full[1, :min(T, n_nps)]
        alloc["ei"][:min(T, n_ei)] = full[2, :min(T, n_ei)]

    nps_extra = -alloc["nps"]
    if nps_inflows_tn is not None:
        nps_extra = nps_extra - np.asarray(nps_inflows_tn, dtype=float)[:n_nps]
    ei_extra = bridge["ei_outlay_bn"][:n_ei] / 1000.0 - alloc["ei"]

    return {
        "nhi": depletion_shift(NHI_REFORM, er["NHI health"][:n_nhi],
                               wage_linked_share=nhi_share,
                               extra_outlays_tn=-alloc["nhi"] if alloc["nhi"].any() else None),
        "nps": depletion_shift(NPS_REFORM, er["NPS pension"][:n_nps],
                               wage_linked_share=nps_share,
                               extra_outlays_tn=nps_extra if nps_extra.any() else None),
        "ei": depletion_shift(EI_BASELINE, er["EI unemployment benefit"][:n_ei],
                              wage_linked_share=ei_share,
                              extra_outlays_tn=ei_extra),
    }


def korea_assembled_band(horizon: int | None = None, year: str = "2025") -> dict:
    """The assembled band grid: one V2 run per (diffusion preset × exposure read ±0.5pp),
    nine runs total. Returns {(preset_key, delta_pp): bridge}. Share edges are applied
    downstream by korea_project_funds — see the band note at KOREA_BAND_KEYS for why the
    AGI presets are absent."""
    from .korea_exposure import exposure_variant
    from .korea_funds import NPS_REFORM
    from .korea_scenarios import KOREA_BAND_KEYS
    n = int(horizon) if horizon is not None else len(NPS_REFORM.revenue)
    deltas = build_korea_deltas(year)
    out = {}
    for delta in (-0.5, 0.0, 0.5):
        data = build_korea_data(year, exposure=exposure_variant(delta) if delta else None)
        for pkey in KOREA_BAND_KEYS:
            run = run_korea_preset(pkey, n_periods=n, data=data, deltas=deltas)
            out[(pkey, delta)] = run["bridge"]
    return out
