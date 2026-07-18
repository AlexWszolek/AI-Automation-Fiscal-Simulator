# Design system — target spec for the post-Streamlit site

The final site will not be Streamlit. This file records the agreed design direction so the
migration implements it rather than rediscovering it. The Streamlit app applies the cheap subset
(near-white surfaces, TNR serif, red/blue semantic colors); everything else waits for the real
front end.

## Layout

- **720px fixed content column** for prose, metrics, and tables; charts and the map may break out
  to ~960px. No full-bleed dashboard layout.
- Spacing pass: consistent vertical rhythm between sections; generous margins; panels only where
  a boundary means something.
- Help affordances recede: no bold ⓘ icons next to every control — quiet hover targets or
  underdotted terms.

## Color

Semantic rule: **red = fiscally bad, blue = good.** No green.

- Bad / losses / deficits: **deep brick / oxblood** (≈ `#8c2f28`)
- Good / gains / recoveries: **muted slate blue** (≈ `#5b7c99`)

Ink scale on warm near-white:

| Role | Value (approx) |
|---|---|
| Near-black ink — body text, headers | `#1a1a18` |
| Dark gray — secondary headers, strong emphasis | `#3d3d3a` |
| Mid gray — captions, labels, the "≈ X×" anchor lines, axis labels | `#6e6e68` |
| Light gray — borders, dividers, inactive tab outlines | `#e2dfd7` |
| Warm near-white — page background (closer to white than cream, per review) | `#fcfbf8` |
| White-ish panel — the lever rail / panels read WHITE | `#fefdfb` |
| Warm off-white — input wells, hover states, table stripes | `#f4f2ec` |

Charts converge on the same rule: distress/loss series in the oxblood family, recovery/good
series in slate blue (e.g. the re-employed workforce band is blue), neutral series in the ink
grays. The categorical 7-color palette is transitional and shrinks as charts adopt red/blue/ink.

## Typography

- **Serif body close to Times New Roman** — the stack is
  `'Times New Roman', Times, 'Liberation Serif', Tinos, serif` (Tinos is the vendored
  metric-compatible fallback). No decorative serifs; policy-document register.
- **Monospace with `font-variant-numeric: tabular-nums` for all data** — metric values, table
  cells, axis labels — so numbers never jitter as scenarios change.
- True minus sign (U+2212 −) in all signed figures, never the ASCII hyphen.

## KPI row

- Two hero metrics: **employment lost (%)** and **cumulative federal income tax lost**; the
  remaining metrics one visual tier down.
- Large figures abbreviate: $2.67T, not $2,674B (tables keep exact $B).
- Reserve fixed vertical space for the grounding anchor line under each metric so the row never
  reflows when captions change length.

## Default scenario

Deferred decision (likely the Acemoglu preset rather than Custom) — revisit at migration time.

## Migration note

Everything that matters is already streamlit-free: `fiscal_model/app_params.py` (UI↔params
bridge + shareable-URL codec), `fiscal_model/charts.py` (pure vega-lite specs), presets,
grounding, summary. Only the widget/layout layer is Streamlit-bound. A static front end embedding
the same vega-lite specs, driven by a precomputed scenario grid plus a small API for custom
configs and the tornado, ports with the conservation machinery untouched.
