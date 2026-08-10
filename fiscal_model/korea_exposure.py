"""The Korea AI-exposure vector — published, complementarity-adjusted, reconciled.

Source: **BOK 이슈노트 2025-2 「AI와 한국경제」** (오삼일·이수민·이하민, Bank of Korea),
<그림 9> 직업별 AI 노출도·보완도 — Felten-AIOE exposure × Pizzinelli complementarity computed
on Statistics Korea's 지역별고용조사 (Cazzaniga et al. 2024 method), by KSCO major group.
Local copy `docs/research/sources/bok-issue-note-2025-2-ai-korean-economy.pdf`. The IMF SIP
2025/013 Figure 7 (`imf-sip-2025-013-ai-korea.pdf`) plots the same authors'-calculation data
and confirms every segment; its Figure 6 credits the Bank of Korea directly.

**How the numbers were obtained, stated plainly:** the figure carries no text-layer values, so
the 27 bar segments were read visually from a 400-dpi render (±0.5pp per segment) and are
accepted only because they reconcile with the aggregates the note PUBLISHES in text: 24%
high-exposure/high-complementarity, 27% high-exposure/low-complementarity, remainder ~49% low
exposure, totals 100%. The asserts below re-check that reconciliation at import; the read is
disclosed as figure-derived wherever these numbers surface externally.

**Mapping to the model — the complementarity adjustment is the point.** The exposure seam wants
the displacement-prone fraction of each group's jobs. Raw exposure would conflate augmentation
with displacement (the research doc §6 warning); this framework splits them, so:

  EXPOSURE_HELC[g] = the group's high-exposure LOW-complementarity employment share of the
                     group's total — the displacement-prone fraction. THE seam input.
  EXPOSURE_HEHC[g] = the high-complementarity share — the augmentation side (survivor-wage /
                     sensitivity work, not displacement).

The structural zeros for the manual groups (agriculture, craft, operators; elementary ≈ 0) do
NOT mean "no automation" — they mean *not AI-cognitive displacement-prone*: those groups are
the model's PHYSICAL channel, gated by `robotics_lag`, exactly the two-channel split the engine
already carries. The Korean AI-cognitive wave is clerical-centred: 사무 종사자 are 17.4% of all
employment and 100% displacement-prone under this classification — the single most
policy-relevant composition fact this vector carries.

Frame caveat, disclosed: 지역별고용조사 covers all employed persons; the cell table covers
establishment-survey wage employees. Within-group fractions transfer across frames to first
order; the difference is a stated limitation, not a correction we invent.
"""
from __future__ import annotations

# <그림 9>, % of TOTAL employment, figure-read (LE = low exposure, HEHC = high exposure high
# complementarity, HELC = high exposure LOW complementarity). occ_code = KSCO 6th major.
FIG9_SHARES = {
    #        LE    HEHC  HELC
    1: (0.0, 1.7, 0.0),      # 관리자 (managers)
    2: (0.9, 16.0, 4.7),     # 전문가 및 관련 종사자 (professionals)
    3: (0.0, 0.0, 17.4),     # 사무 종사자 (clerical)
    4: (10.8, 0.0, 1.3),     # 서비스 종사자 (service)
    5: (0.3, 5.5, 3.2),      # 판매 종사자 (sales)
    6: (5.5, 0.0, 0.0),      # 농림어업 (agriculture/fishery)
    7: (8.0, 0.0, 0.0),      # 기능 종사자 (craft)
    8: (10.5, 0.0, 0.0),     # 장치·기계 조작 및 조립 (operators/assemblers)
    9: (13.3, 0.6, 0.0),     # 단순노무 (elementary)
}

# published aggregates the read must reconcile to (note text, p. 5-6); tolerance covers the
# ±0.5pp-per-segment read error
_PUBLISHED = {"HEHC": 24.0, "HELC": 27.0, "TOTAL": 100.0}
_TOL = 1.0

_le = sum(v[0] for v in FIG9_SHARES.values())
_hehc = sum(v[1] for v in FIG9_SHARES.values())
_helc = sum(v[2] for v in FIG9_SHARES.values())
assert abs(_hehc - _PUBLISHED["HEHC"]) < _TOL, f"HEHC read {_hehc} vs published 24"
assert abs(_helc - _PUBLISHED["HELC"]) < _TOL, f"HELC read {_helc} vs published 27"
assert abs(_le + _hehc + _helc - _PUBLISHED["TOTAL"]) < _TOL, "figure read does not total 100%"

# within-group fractions — frame-consistent (numerator and denominator from the same figure)
EXPOSURE_HELC = {g: (v[2] / sum(v) if sum(v) else 0.0) for g, v in FIG9_SHARES.items()}
EXPOSURE_HEHC = {g: (v[1] / sum(v) if sum(v) else 0.0) for g, v in FIG9_SHARES.items()}
