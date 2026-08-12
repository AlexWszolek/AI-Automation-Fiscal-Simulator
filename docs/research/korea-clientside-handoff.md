# Handoff: move the Korea interactive model client-side

**For a session picking this up cold.** Read `docs/research/korea-port-brief.md` first for the
project, then this file for the change. Companion state: the `korea-port-project` memory and
`docs/research/korea-fiscal-system.md` (✓/⚠ convention).

---

## 0. The decision and why

Move the computation behind `/korea-app.html` from the server (`/api/korea/run`,
`/api/korea/tornado`) into the browser. The Python model stays canonical; the browser runs a
**fixture-pinned mirror**.

Why this is right for Korea and wrong for the US (adjudicated 2026-08-12, after an adversarial
review of the hosting budget):

- **The arithmetic is tiny.** 209 occupation×wage-bracket cells (vs 33,369 US), and Korean
  transfers are closed-form statutory formulas (EI benefit, EITC trapezoids, Basic Pension) —
  there is **no analogue of the US 2.1M-interpolation transfer-grid machinery**, which is 60% of
  the US per-run cost. A Korea run is ~10⁵–10⁶ flop-equivalents; the measured 10ms/draw in Python
  is mostly small-array dispatch overhead. In JS: sub-millisecond per draw, full 400-draw tornado
  in a few hundred ms on the main-thread-free path.
- **Restricted-network briefing rooms.** The policymaker audience sits behind ministry firewalls.
  A fully client-side page (map topojson already self-hosted) works on any network that can load
  one page, and can be handed to the diplomacy org as a file. The server version cannot have this
  property.
- **Resilience + cost.** The Korea site becomes static: CDN-cached, no process to crash the week
  the deck circulates. The server ask shrinks to US-model-only (~$650/yr, one 8-core box).
- **The template for countries 3–12.** Future reduced-form country models follow the Korea shape;
  this port is the pattern they'll reuse.

Why NOT to hand-port casually: the Korea work has already produced **two silent-`getattr` bugs in
the funds bridge alone** — a parallel arithmetic path read a nonexistent attribute and quietly
produced wrong headline numbers, twice. Both were caught by reconciliation tests pinning the
bridge to the engine's own lines. A JS mirror without an equivalent pin **is** that bug class,
permanently. The entire design below exists to prevent it.

## 1. Non-negotiables

1. **Timing gate: do NOT start before the September presentation is delivered.** Numbers freeze
   ~Aug 26; the API version is built, parity-tested, and ships the event. This port is the
   post-event upgrade. If you are reading this before the event: stop.
2. **Python stays canonical, permanently.** Report artifacts, deck numbers, committed bundles,
   and the numbers-freeze all come from the Python engine. The JS engine is a mirror whose only
   authority is "equal to the fixtures Python generated." Never fix a JS/Python discrepancy by
   changing Python to match JS.
3. **Copy discipline.** Every user-facing string is a `[copy: Alex]` placeholder or lives in
   copy.json (canonical). The port moves computation, not words. Do not author, move, or "improve"
   copy.
4. **Push only on Alex's explicit word.** Commit locally at phase boundaries.
5. **The standing cost is real — state it, don't hide it.** After this ships, every Korea model
   change lands twice: Python change → fixtures regen → JS mirror updated. The fixture chain (§3)
   makes forgetting loud, but the second implementation is a permanent maintenance surface. That
   trade was accepted deliberately (offline capability + resilience + the country template); if a
   future maintainer finds the mirror rotting, the correct retreat is back to the API, not a
   silently stale mirror.

## 2. Scope

**In:** the computation behind `/korea-app.html` — `build_korea_scenario_payload` and
`korea_mc_tornado` (both in `fiscal_model/korea_webpayload.py`), consumed today via
`api/korea.py` and `web/src/korea/useKoreaScenarioData.ts`.

**Out, untouched:** the US model and site (server stays authoritative); `/korea.html` presenter
view and `/korea-slides.html` (already static); the Python Korea modules themselves (they remain
the source of fixtures and all publication numbers); all copy.

**Deferred decision, default = keep:** the committed Korean static bundles. Keep them for
first-paint (fast initial render, and they double as in-prod parity oracles — see §5 runtime
self-check); the client engine takes over on first interaction.

## 3. Architecture — the fixture chain is the whole design

```
fiscal_model (canonical Python)
   │  scripts/gen_korea_fixtures.py  (deterministic: fixed seeds, sorted keys, no timestamps)
   ▼
web/src/korea/engine/fixtures/*.json     (COMMITTED golden payloads + draw arrays)
   │                                      │
   │ pytest gate:                         │ vitest gate:
   │ test_korea_fixtures_fresh —          │ engine.test.ts — the JS engine must
   │ regenerating must reproduce the      │ reproduce every fixture payload at
   │ committed files byte-for-byte        │ display precision
   ▼                                      ▼
 any Python model change → pytest red → regen fixtures → vitest red until the JS mirror follows
```

This is the same loud-drift pattern as `test_copy_json_fresh` and the cfg_repr staleness gates.
Both gates must exist before the first line of engine port is written.

**Fixture coverage** (generated from Python, one file per case):
- every preset × overlay subset × demography variant (저위/중위/고위) — pristine payloads
- a lever sweep: each of the 25 levers at min/mid/max off a central config, plus ~20 random
  jointly-perturbed configs (fixed seed)
- tornado fixtures: full tornado output for ≥3 configs (pristine + modified), N as shipped
- edge cases: every guard the Python engine raises on (out-of-grid levers, invalid overlay
  pairs) — the JS engine must reject the same inputs

**What ships to the browser** (a few hundred KB total, no runtime fetches beyond the page):
- the baked 209-cell table (NOT the 34MB `data/raw/korea/` XML — bake via `korea_assembly`)
- published fund paths, demography variants, grid/preset/overlay definitions
- **the pre-drawn MC factor arrays** — see §4

## 4. Parity spec

- **The bar is display-precision equality** — payloads round for display, so assert equality on
  the rounded values, with a secondary tolerance check (rtol 1e-9) on raw floats to catch drift
  early. Bitwise equality is NOT required — but will usually hold, because JS is spec-mandated
  IEEE-754 double with **no FMA contraction** (the divergence we caught inside numpy itself —
  see `reabsorption._interp_rows`'s docstring — cannot happen in JS).
- **Known divergence source #1: `np.sum` pairwise summation.** A naive JS loop sums
  left-to-right; numpy blocks pairwise. For 209-element arrays the difference is ~1e-15 relative
  — inside tolerance, but if a fixture fails on a sum, replicate numpy's blocking rather than
  loosening the gate.
- **Known divergence source #2: the RNG. Do not port PCG64.** `korea_mc.py:114` uses
  `np.random.default_rng(seed+1)` uniforms. Ship the drawn factor arrays as a fixture (they are
  config-independent draws applied multiplicatively — verify this by reading `korea_mc.py`
  before assuming; if any draw depends on the config, ship the underlying uniforms instead).
  JS consumes the arrays; tornado fixtures then pin the whole chain.
- **Language: TypeScript** under `web/src/korea/engine/`, tested with the existing vitest setup.
  No new runtime dependencies; no WASM (unnecessary at this size).

## 5. Phases

**Phase 0 — enumerate the live slice (½ day, with an abort checkpoint).**
`korea_assembly` runs the full V2 assembly on Korean data. Before estimating anything, read
`korea_assembly.py`, `korea_webpayload.py` (369 lines), and trace exactly which engine code paths
execute for Korea (`close_state_gaps` must NOT be one of them — formula-transfer country; which
survivor/reabsorption/disposition paths ARE live?). Deliverable: a list of every function the
port must mirror, with line counts. **Checkpoint: if the live slice exceeds ~1,500 lines of
Python, stop and report before porting** — the cost/benefit was estimated on the reduced chain
(~2,435 total Korea lines, of which the payload path is a subset), and a much larger slice
changes the decision.

**Phase 1 — fixture harness first.** `scripts/gen_korea_fixtures.py` + the pytest freshness gate
+ a vitest suite that loads fixtures and fails (no engine yet). Commit. From here, progress is
"make fixtures pass," which keeps the port honest.

**Phase 2 — port the engine slice.** Bottom-up: payroll components → tax chain → transfers →
demography → erosion paths → funds bridge/projector → payload assembly → tornado. Make each
layer's fixtures pass before the next. The funds bridge is where both silent-getattr bugs lived —
port it against the reconciliation-test fixtures, not against the bridge code alone.

**Phase 3 — integrate.** `useKoreaScenarioData.ts` calls the local engine instead of fetch;
tornado in a Web Worker (keep the existing progressive-partial UX); static bundles remain the
first-paint source. Add the **dev-build runtime self-check**: on load, recompute one bundled
preset payload locally and `console.assert` equality with the fetched bundle — every dev session
becomes a parity test.

**Phase 4 — verify offline + retire the API.** Full verification (§6). Then: keep
`/api/korea/*` live but unused for one deploy (feature-flag fallback), then delete the routes,
`api/korea.py`'s service wiring, and the Caddy block. Update the deploy notes. The Python Korea
modules are NOT deleted — they are the fixture source forever.

## 6. Verification checklist

- [ ] pytest fixture-freshness gate green; full suite green (baseline 434 + new)
- [ ] vitest: every fixture payload reproduced at display precision (baseline 222 + new)
- [ ] DevTools Network: **zero requests** during slider drags and tornado runs
- [ ] Airplane-mode test: load `/korea-app.html`, then disconnect — everything still works,
      including the map (self-hosted topojson) and tornado
- [ ] Tornado completes < 1s in-browser; UI thread stays responsive (Worker)
- [ ] Mobile: 375×812 preview + a CPU-throttled run (the audience opens this on phones)
- [ ] The dev runtime self-check passes on every preset
- [ ] Headline numbers on the rendered page match the frozen deck numbers exactly
      (NHI 0.23–0.90yr central 0.50; EI ₩2.6–11.4tn central 5.5; NPS 0.49–2.44 of 8;
      AGI-5y 2.14yr / ₩59.5tn / 7.46 of 8 — as pinned in the korea-port-project memory)
- [ ] Commit per phase; **no push without Alex's word**

## 7. Risks, ranked

1. **Silent divergence** — the getattr precedent. Mitigated by the fixture chain; defeated only
   if someone bypasses it. Never merge a JS change that isn't fixture-covered.
2. **Phase-0 scope surprise** — the V2 assembly may exercise more engine than the reduced-chain
   estimate assumed. That's what the checkpoint is for; the retreat (stay server-side) is cheap
   and loses nothing that exists today.
3. **Dual maintenance rot** — §1.5. The gates make it loud; the memory note should record that
   the mirror exists so future sessions budget for it on every Korea model change.
4. **RNG subtleties** — defeated by shipping draws, but only if the config-independence
   assumption in §4 is verified by reading, not assumed.

## 8. Consequences elsewhere when this ships

- **Hosting**: server = US model only; one 8-core box (~$650/yr) + CDN. The Seoul-satellite and
  geo-routing questions are closed, not deferred.
- **Grant text**: "country models run client-side (server-free, functional on restricted
  government networks); the server serves only the US model's heavy computation and Monte Carlo."
- **Countries 3–12**: this port is the template — new reduced-form countries target the JS
  engine + fixture pattern from day one, with Python as the authoring/verification side.
- **Memory**: update `korea-port-project` (architecture line + the dual-maintenance cost) when
  Phase 4 completes.
