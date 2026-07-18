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
artifact is stale — the test suite tells you).

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
