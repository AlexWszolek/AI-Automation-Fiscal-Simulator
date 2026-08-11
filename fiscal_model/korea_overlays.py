"""The two Korean policy overlays — the fed-vat / swf analogues the research doc flags as
LIVE Korean policy questions (korea-fiscal-system.md §Channel 3: VAT headroom; §5: the
Korinek instrument mix).

kr-vat — "+1pp statutory VAT (10% → 11%)".
    The engine's federal-VAT channel (Korinek-Lockwood stage 1) levies on a stylized
    2/3-of-value-added base. Korea's STATUTORY-EFFECTIVE base is far smaller — exemptions,
    zero-rating, the simplified regime — and is measured directly from receipts:
    ₩79.2tn collected in 2025 at 10% (NABO 나보포커스 제137호 [표 1], 2026-02-12,
    sources/nabo-focus-137-tax-revenue-2025.pdf) → base ₩792tn ≈ 29.8% of GDP.
    The overlay therefore presents a STATUTORY +1pp and applies the engine rate that
    yields the same year-0 revenue on the stylized base: 0.01 × 792tn / (2/3 × GDP).
    The engine's withdrawal drag still erodes the base as displacement rises (that
    linkage is the point of running it through the model rather than a flat ₩7.9tn/yr).

kr-nps-mandate — "NPS automation dividend — 20% of AI profits".
    The swf overlay's mechanism pointed at the pension fund: a mandated National Pension
    Service equity share of after-tax automation profits, so fund revenue scales with the
    shock instead of the payroll base. 20% mirrors the US swf overlay (illustrative, not
    derived). Implemented WITHOUT touching the treasury ledger: the mandated flow is 20% of
    the run's own undistributed-automation-profit path, added to NPS reserves at the
    projector (extra inflows) — the deficit line never sees the money, so nothing is
    double-counted across charts. Readout: how many of the given-back years it buys back.
"""
from __future__ import annotations

from dataclasses import dataclass

from .country import KOREA

KR_VAT_REVENUE_2025_TN = 79.2      # ₩tn collected at the 10% statutory rate, 2025 실적
KR_VAT_STATUTORY_RATE = 0.10
KR_VAT_SOURCE = ("NABO 나보포커스 제137호 「2025년 국세수입 실적 및 세목별 증감원인」 "
                 "[표 1] (2026-02-12): 부가가치세 2025 실적 ₩79.2조")
NPS_MANDATE_PROFIT_SHARE = 0.20    # mirrors the US swf overlay's illustrative 20%


def kr_vat_engine_rate(statutory_pp: float = 0.01) -> float:
    """The engine fed_vat_rate whose year-0 revenue equals `statutory_pp` on Korea's
    statutory-effective base (receipts/rate), levied on the engine's stylized 2/3-VA base."""
    effective_base = KR_VAT_REVENUE_2025_TN / KR_VAT_STATUTORY_RATE * 1e12
    return statutory_pp * effective_base / ((2.0 / 3.0) * KOREA.va_baseline)


@dataclass(frozen=True)
class KoreaOverlay:
    key: str
    params: dict                   # V2Params fields applied to the MAIN run ({} = readout-only)
    provenance: str


KOREA_OVERLAYS: dict[str, KoreaOverlay] = {o.key: o for o in [
    KoreaOverlay("kr-vat", params={"fed_vat_rate": kr_vat_engine_rate(0.01)},
                 provenance=f"{KR_VAT_SOURCE}; statutory-effective base ₩792tn ≈ 29.8% of "
                            "GDP vs the engine's stylized 2/3 — engine rate calibrated to "
                            "equal year-0 revenue; VAT unchanged at 10% since 1977, 15.3% "
                            "of tax revenue vs OECD 20.5% (research doc §Channel 3)"),
    KoreaOverlay("kr-nps-mandate", params={},
                 provenance="swf-overlay mechanism (Korinek-Lockwood equity share) pointed "
                            "at the NPS; 20% mirrors the US overlay (illustrative). Flow = "
                            "20% × the run's undistributed-automation-profit path, added "
                            "at the projector — never through the treasury ledger"),
]}
