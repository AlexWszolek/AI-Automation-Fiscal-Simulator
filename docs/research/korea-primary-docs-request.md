# Primary documents — status (resolved 2026-08-07) and residual asks

**Original purpose of this note:** a forwardable request to the diplomacy organisation for the
three primary documents behind the presentation's headline claims. **That request is no longer
needed.** All three were retrieved directly from NABO the same morning (browser User-Agent on
`nabo.go.kr/board/file/down.do?fid=…`; details in `sources/README.md`):

| Needed | Got | Status |
|---|---|---|
| Employment Insurance fund accounts | NABO FY2025 settlement analysis (labor-committee volume) + 「2026 대한민국 사회보험」, citing MOEL's FY2025 fund settlement report | ✓ headline claims primary-sourced; §2.3 corrected (statutory bands are per-account) |
| NABO health & LTC projection | NABO Focus 162 (2026-06-09) — supersedes the 2023–2032 report | ✓ §2.1 corrected (depletion 2031 baseline / 2029 with reform); **year-by-year 2026–2035 paths in hand** |
| NABO 2025–2072 long-term projection | NABO Focus 92 (2025-02-27) | ✓ scenario variants pinned (163.2%–181.9%); pre-reform NPS 2057 vintage noted |

The Aug-14 re-scope tripwire is therefore **cleared on the document front** — the model-backed
version of the presentation is unblocked as far as inputs go.

## ~~NEW ask~~ RESOLVED 2026-08-10 — Alex delivered all three (exposure join unblocked)

The model needs a published **AI-exposure vector at occupation major-group level**. The KDI
monograph (now in `sources/`) publishes lists and aggregates but no full vector, and the three
sources that do are behind bot-walls our tooling cannot pass. **Any ONE of these, in order of
preference:**

1. **OECD, *Artificial Intelligence and the Labour Market in Korea* (Oct 2025)** — the PDF *and,
   more importantly, the StatLink data files* (each figure in OECD reports carries a `stat.link`
   URL serving the underlying numbers as Excel). The exposure-by-occupation figure's data file is
   exactly what we need. https://doi.org/10.1787/68ab1a5a-en
2. **한지우·오삼일, 「AI와 노동시장 변화」, 한국은행 BOK 이슈노트 제2023-30호** — the PDF (its
   exposure-by-occupation figures/appendix). Search "BOK 이슈노트 AI와 노동시장" on bok.or.kr.
3. IMF Selected Issues Paper 2025/013, *Transforming the Future: The Impact of AI in Korea*
   (https://www.elibrary.imf.org/view/journals/018/2025/013/article-A001-en.xml).

## Residual asks (low priority, none blocking)

1. ~~Post-reform NPS fund path~~ **RESOLVED 2026-08-10 by fetch**: NABO 현안보고서 「2025년
   국민연금법 개정의 재정 및 정책효과 분석」 (June 2025), [표 25] — knots 2025–2095 incl. a
   separate contributions column; deficit 2047, depletion **2065**. In `sources/`.
2. **Full 「2025~2072년 장기재정전망」 report PDF** — the Focus 92 brief pins every number we
   quote; the full report adds year-by-year detail only.
3. **MOEL microdata application** (마이크로데이터신청, `laborstat.moel.go.kr`) for sub-major-group
   KSCO occupation detail — only if the 10-major-group granularity proves insufficient after the
   cell structure is built. Korean-language process; unknown turnaround.
