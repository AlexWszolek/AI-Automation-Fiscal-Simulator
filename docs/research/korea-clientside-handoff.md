# Handoff: move the Korea interactive model client-side (Pyodide)

**For a session picking this up cold.** Read `docs/research/korea-port-brief.md` first for the
project, then this file for the change. Companion state: the `korea-port-project` memory and
`docs/research/korea-fiscal-system.md`.

**Revision note (2026-08-12).** The first version of this handoff planned a TypeScript rewrite of
the Korea engine, pinned to Python by golden fixtures. Alex challenged the premise — *why rewrite
at all when Pyodide runs the actual engine in a Web Worker?* — and he was right: the entire risk
apparatus of the old plan (fixture-pinned mirror, dual maintenance, the silent-getattr bug class)
existed to manage the dangers of a second implementation. Running the same Python eliminates the
class instead of managing it, which is this project's house philosophy. The JS engine survives
only as Appendix A with an explicit trigger condition.

---

## 0. The decision and why

Run the existing Korea engine — `fiscal_model.korea_webpayload.build_korea_scenario_payload` and
`korea_mc_tornado`, unmodified — **in the browser under Pyodide, inside a Web Worker**, replacing
the `/api/korea/*` calls. Python remains the one and only implementation.

Why client-side at all (unchanged from the original analysis):
- 209 cells, closed-form transfers — the computation is tiny; the server buys nothing but latency
- **Restricted-network capability** for a ministry-firewalled audience; resilience (no process to
  crash the week the deck circulates); $0 Korea hosting; the template for countries 3–12
- The server ask shrinks to US-model-only (~one 8-core box)

Why Pyodide and not a JS rewrite:
- **Same code = no drift class.** The funds bridge that produced two silent-getattr bugs is the
  same bridge, byte for byte. No mirror to maintain, no fixture chain as a load-bearing firewall
  (fixtures survive only as a cheap parity-test corpus, §4).
- **Feasibility is already strong on inspection** (verified 2026-08-12): the Korea path's data
  inputs are stdlib `csv` reads of committed tidy CSVs (`korea_cells.py:71`,
  `korea_assembly.py:54`) — no parquet, no lxml at runtime. Third-party surface is numpy + pandas
  (+ their optional accelerators `pyarrow`/`numexpr`, which Pyodide's pandas runs without — spike
  confirms). scipy was never a dependency, by long-standing project rule.
- Cost: ~2–4 days against ~a week-plus for the rewrite, with near-zero ongoing cost instead of a
  permanent dual-maintenance surface.

## 1. Non-negotiables

1. **Python canonical** — now trivially true: the browser runs the canonical code. Never patch
   model behaviour inside the worker shim; any numeric change happens in `fiscal_model` and flows
   everywhere.
2. **Copy discipline.** `[copy: Alex]` placeholders and copy.json canonical. This change moves
   computation, not words.
3. **Push only on Alex's explicit word.**
4. **Timing** (settled 2026-08-12, superseding the original hard gate): **Phase 0 + the parity
   corpus may run now** — they are zero-production-risk and de-risk the estimate. **The swap
   itself** (flag on, API retired) waits on two things: the Phase-0 checkpoint numbers, and
   Alex's call on whether the offline capability should ship *at* the September event (in which
   case: port in the post-freeze window, org reviews with the flag ON, minimum one week of soak)
   or after it (default). The reviewed artifact must be the shipped artifact.

## 2. Scope

**In:** the compute behind `/korea-app.html` — payload builds and tornado, currently served by
`api/korea.py` and consumed by `web/src/korea/useKoreaScenarioData.ts`.

**Out, untouched:** the US model and site; `/korea.html` presenter view; `/korea-slides.html`;
all copy. The Python Korea modules are the thing being *shipped*, not replaced.

**Kept:** the committed Korean static bundles as the first-paint source (instant render while the
worker warms) and as in-production parity oracles (§5 self-check).

## 3. Architecture

```
page load ──► static bundle paints the default scenario immediately (as today)
     │
     └─► Web Worker starts in background:
           load pyodide.js + numpy + pandas (~25–30MB, service-worker precached)
           micropip-install fiscal_model wheel (pure Python, built by CI)
           load baked Korea data (tidy CSVs / npz, a few hundred KB)
           warm-up: one payload build, self-check vs the fetched bundle
     │
slider/tornado ──► worker.postMessage(cfg) ──► sanitize_korea_config + payload/tornado
                                              (the SAME functions api/korea.py calls)
                   ◄── JSON payload (identical schema; useKoreaScenarioData swaps
                       fetch() for worker call behind a feature flag)
```

- **Wheel**: `fiscal_model` packaged as a pure-Python wheel; the only new packaging artifact.
- **Data**: the committed tidy CSVs ship as static assets; a small loader seam lets
  `korea_assembly` read them from a supplied directory/bytes instead of the repo path. No 34MB
  raw XML in the browser.
- **Fallback**: the feature flag keeps `/api/korea/*` as the fallback path for one deploy after
  the flag defaults on; then the routes, `api/korea.py` wiring, and the Caddy block retire. The
  Python modules obviously remain.

## 4. Parity — a test, not a firewall

The old plan needed fixtures as the *only* thing standing between two implementations. Now parity
is a regression test against environment differences (WASM numpy build, Pyodide's pinned
numpy/pandas versions vs the repo's):

- **Bar: display-precision equality** of payloads (they round for display), with a secondary
  rtol-1e-9 raw check. Ulp-level divergence is expected and acceptable — precedent: numpy's own
  macOS-arm64 FMA contraction found in the `_interp_rows` work. (WASM, like JS, mandates plain
  IEEE-754 doubles with no scalar FMA — so the browser may actually match the Linux server more
  closely than the Mac matches either.)
- **Corpus**: `scripts/gen_korea_fixtures.py` emits golden payloads (presets × overlays ×
  demography variants + a lever sweep + ≥3 tornado cases). A vitest/worker test replays them
  through Pyodide and asserts. Record the Pyodide, numpy, and pandas versions in the report.
- **RNG**: no porting question anymore — `korea_mc.py`'s `default_rng(seed+1)` runs as-is. Seeded
  determinism within a given numpy build; cross-build tornado equality asserted at display
  precision like everything else.

## 5. Phases

**Phase 0 — feasibility spike (~half a day), with measured checkpoints.**
Build the wheel, load it in Pyodide in a worker, run one `build_korea_scenario_payload` and one
tornado. Report four numbers:
1. Cold worker-ready time (desktop + a throttled/mobile profile)
2. Payload-build latency in-worker
3. **Tornado wall time** — the known risk: Korea's 10ms/draw is small-array *dispatch* overhead,
   and Pyodide's interpreter is ~3–5× slower, so 400 draws could land anywhere from 5s to 60s
4. Peak WASM heap (phone RAM matters for the briefing-room audience)

**Abort criteria:** a hard pyarrow-style dependency that can't be shimmed; tornado >5s *after*
Phase 3's batching; worker unusable on a mid-range phone profile. Retreat = stay server-side,
lose nothing.

**Phase 1 — loader seam + shipped data + parity corpus.** The `korea_assembly` read-from-bytes
seam (native path unchanged and default); baked data as static assets; fixture generator + the
freshness pytest gate; the parity replay test. No production change.

**Phase 2 — worker bridge + integration behind the flag.** `useKoreaScenarioData.ts` calls the
worker when the flag is on; the warm-up self-check (recompute one bundled preset, assert equality
with the fetched bundle — every session becomes a parity test); progressive tornado partials
stream from the worker exactly as they do from the API today.

**Phase 3 — tornado performance, in Python, canonically.** If Phase 0's tornado number is poor,
the fix is **batching the 400 draws across numpy** — at 209 cells a (400, 209) vectorization is
straightforward, it amortizes the dispatch overhead that dominates, and it speeds the *server*
path identically. It is a canonical optimization with a plain parity test (same draws, same
results at display precision), not a browser-side hack.

**Phase 4 — offline + retirement.** Service-worker precache of pyodide + wheel + data (offline
after first visit — the PWA story); the verification battery; flag defaults on; one-deploy
fallback window; retire `/api/korea/*`; update deploy notes and the `korea-port-project` memory.

## 6. Verification checklist

- [ ] Parity corpus green in CI (Pyodide replay ≡ native fixtures at display precision)
- [ ] Warm-up self-check passes on every preset
- [ ] DevTools Network: zero requests during slider drags and tornado runs
- [ ] Offline test: load once, go offline, reload — everything works including map + tornado
- [ ] Tornado ≤ ~3s in-worker on desktop, tolerable on a throttled phone; UI thread never blocks
- [ ] Mobile: 375×812 + CPU-throttled run; peak memory recorded
- [ ] Headline numbers on the rendered page match the frozen deck numbers exactly
      (NHI 0.23–0.90yr central 0.50; EI ₩2.6–11.4tn central 5.5; NPS 0.49–2.44 of 8;
      AGI-5y 2.14yr / ₩59.5tn / 7.46 of 8 — as pinned in the korea-port-project memory)
- [ ] Full pytest + vitest suites green; commit per phase; no push without Alex's word

## 7. Honest costs and risks

1. **~25–30MB runtime download** (pyodide + numpy + pandas, compressed; cached thereafter).
   Mitigated by background worker load behind the instant static first paint. Still a real cost
   on hotel/mobile connections the first time.
2. **Tornado latency under the WASM interpreter** — the one number that can kill this. Phase 0
   measures it; Phase 3's batching is the fix; the abort criterion is explicit.
3. **Phone memory** (~150–300MB WASM heap with pandas). Measured at Phase 0 on a throttled
   profile; the static-first page remains fully functional for anyone whose device declines the
   worker.
4. **Pyodide version pinning** — its numpy/pandas lag the repo's. Display-precision parity
   absorbs this; the corpus test catches a Pyodide upgrade that doesn't.
5. **True file-handoff remains unsolved** — WASM loading breaks under `file://`. Offline-after-
   first-visit (PWA) works; a genuinely networkless single-file artifact does not. See Appendix A.

## Appendix A — the TypeScript engine (rejected default, one trigger)

The original plan: hand-port the Korea chain to TS, pinned by the fixture chain (pytest freshness
gate → committed fixtures → vitest parity gate), display-precision bar, ship the drawn MC factor
arrays rather than porting PCG64, np.sum pairwise blocking as the known divergence source. It
costs ~a week plus a **permanent dual-maintenance surface** — every Korea model change lands
twice, forever — and its failure mode is the silent-getattr bug class that already happened twice
in the bridge.

**Trigger to revisit:** the diplomacy org needs a *genuinely networkless, single-file* artifact —
open `index.html` from a USB stick in an air-gapped room. A ~100KB JS engine inlines into one
HTML file; a 30MB WASM stack under `file://` does not. If that deliverable is ever requested,
build the TS engine *then*, against the same fixture corpus §4 already maintains. Until then,
don't.
