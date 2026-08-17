# Deploying the website

Two pieces: a **static site** (`web/dist`) and a small **compute service** (`api/`). The site is
fully browsable with the compute service down — every preset × policy-response combination and
their sensitivity tornados are committed static files; the service exists only for custom slider
values and modified-config tornados. Nothing on the page calls any host but its own origin
(fonts, map shapes, and data are all self-hosted), so it works in a briefing room with
restricted network.

## Build

```bash
# model artifacts (once per machine; see the main README's Setup)
bash scripts/bootstrap.sh

# python env for the compute service
uv pip install -r requirements.txt -r api/requirements.txt

# the static site
cd web && npm ci && npm run build          # -> web/dist
```

If model code or presets changed, regenerate the committed bundles first:
`python scripts/gen_web_bundle.py` (and `python scripts/precompute_app_mc.py` if the tornado
artifact is stale — the test suite tells you). For the Korea pages the equivalents are
`scripts/gen_korea_bundle.py`, `scripts/gen_korea_scenarios.py`, and `scripts/gen_korea_grid.py`
— all gated by staleness tests, so a green suite means the committed bundles are current.

## The Korea site

The same build serves three additional entries, all unlisted (noindex): `/korea.html`
(the static presenter view), `/korea-app.html` (the interactive site with levers, overlays,
and the EN/KR toggle — `?lang=ko` deep-links Korean), and `/korea-slides.html` (the deck).
They are fully static except custom slider values and live tornados, which use
`/api/korea/*` on the same compute service — restart it after pulling so the Korea routes
load. `bash scripts/bootstrap.sh` builds the gitignored Korea tidy tables the service needs
(step 7; from committed raw exports, no network).

## Serve

- Copy `nginx.conf.example` **or** `Caddyfile.example`; static root = `web/dist`, `/api`
  proxied to `127.0.0.1:8000`.
- Copy `fiscal-api.service.example` to systemd for the compute service.
- Health check: `curl localhost:8000/api/health`.

## Cutting over from Streamlit Cloud

Old shared `*.streamlit.app` links keep working only if the Streamlit deployment becomes a
redirect stub: replace the app body with a page that forwards to the new domain **carrying the
query string** (`?preset=…&…` — the new site resolves the same URL format via the ported codec).
Keep the stub deployed for as long as old links matter.
