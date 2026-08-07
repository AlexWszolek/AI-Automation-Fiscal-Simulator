# Primary source documents — Korea port

Retrieved 2026-08-07 directly from `nabo.go.kr` (plain `curl` with a browser User-Agent; the
download endpoint is `https://www.nabo.go.kr/board/file/down.do?fid=<FID>`). All are official
NABO (국회예산정책처, National Assembly Budget Office) publications. These are the primary
citations behind the headline claims in `../korea-fiscal-system.md` — and two of them contain the
published fund paths that feed the fund-depletion projector.

| File | What it is | FID | Supports |
|---|---|---|---|
| `nabo-focus-92-longterm-2025-2072.pdf` | NABO Focus No. 92 (2025-02-27): 2025–2072 long-term fiscal projection summary | fetched via `JSPservlet/download.jsp` link in research doc | Debt ₩1,270.4tn→₩7,303.6tn, 47.8%→173.0% of GDP; potential growth →0.3%; scenario variants 163.2%–181.9%; full fiscal aggregates at 2025/30/40/50/60/72. **Pre-reform NPS depletion 2057** (peak 2039); 사학연금 2042 |
| `nabo-focus-162-nhi-reestimate-2026-2035.pdf` | NABO Focus No. 162 (2026-06-09): NHI re-estimation reflecting medical-reform implementation plans 1·2 | 33319309 | **The health headline.** Deficit from 2026; reserves depleted 2031 baseline / **2029 with medical-reform investment**; annual balances −5.2/−8.0/−9.4/−8.7 ₩tn (2026–29); +₩27.8tn ten-year deficit. Year-by-year revenue/expenditure/reserve paths 2026–2035 with rate assumptions (8% statutory cap binds 2032) — **projector input** |
| `nabo-focus-84-nhi-projection-2024.pdf` | NABO Focus No. 84 (2024-12-20): predecessor NHI projection | 33318361 | Methodology lineage for Focus 162 (which supersedes it) |
| `nabo-nhi-projection-2023-2032-full.pdf` | Full report: 2023~2032 건강보험 재정전망 (Oct 2023) | 33317716 | Older vintage (deficit 2024, depletion 2028 — superseded by Focus 162). Kept for methodology: policy scenarios, required-rate calculations |
| `nabo-settlement-fy2025-labor-committee.pdf` | 결산분석시리즈 IV: FY2025 settlement analysis, labor committee volume | 33319415 | **The EI headline.** Unemployment-benefit account FY2021–25 settlement: FY2025 spend ₩17.46tn, balance −₩1.78tn, reserves ₩1.73tn nominal / **−₩5.99tn net of PCMF borrowings, ratio 0.1×** (p. ~200) |
| `nabo-social-insurance-2026.pdf` | 2026 대한민국 사회보험 (NABO annual, 452 pp) | 33319376 | Whole-EI-fund [표 149]: FY2025 balance **−₩592bn**, reserves ₩7.8tn nominal / **₩79.6bn net** — citing MOEL's own 「2025회계연도 고용보험기금 결산보고서」 (2026-06). Statutory bands per account (고용보험법 §84: benefit account 1.5–2×, stabilization 1–1.5×). [표 151] EI baseline path 2026–29. Reference for all five schemes' 2026 rates and fund structures |

Notes:
- NABO Focus 162 footnote: Focus No. 163 (2026-06-11) covers comparative NHI revenue structures
  ("보험료만으로 지속 가능한가") — relevant to the VAT/funding-mix argument, not yet pulled.
- The full 2025–2072 long-term report PDF (behind Focus 92) has not been pulled; the Focus brief
  pins every number we quote, including the scenario variants.
- The 사회보험 annual [표 151] projection is NABO's Oct 2025 mid-term projection based on 2024
  actuals; FY2025 outturn (−₩1.78tn benefit-account balance) already undershoots it. It shows
  whole-fund reserves rebuilt to ₩21.8tn by 2029 — driven by planned PCMF borrowings and the
  stabilization account's surplus, not by the benefit account healing.
