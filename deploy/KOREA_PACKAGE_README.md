# Fiscal Consequences of AI Automation — Korea site package

This package contains everything needed to host the Korea site: the four pages prebuilt
as static files, the compute service behind the interactive sliders, the model and data
they run on, the source to rebuild the site, and the deck and methodology documents.
`VERSION` holds the source commit it was cut from.

## What is in it

| Path | What |
|---|---|
| `web/dist/` | The site, prebuilt. Four pages: `korea.html` (presenter view), `korea-app.html` (interactive, with levers and the EN/KR toggle), `korea-dash.html` (the seminar screen), `korea-slides.html` (the deck). `index.html` links to the four. |
| `api/`, `fiscal_model/` | The compute service (FastAPI) and the model it runs. |
| `data/raw/korea/` | The Korean source tables: raw exports as served (`*.xml.gz`, `*.xlsx`) and the parsed tables the service reads (`*.tidy.csv`). |
| `web/` | The site's source (Vite + React). Rebuild with `npm ci && npm run build`. |
| `scripts/` | Regeneration: the committed data bundles, the lever grid, the deck PNGs, the methodology PDF. |
| `tests/` | The Korea test suite (`pytest tests`). |
| `deploy/` | nginx and Caddy site configs, a systemd unit for the service. |
| `docs/research/korea-slides-pack/` | `about-the-model.pdf` (methodology, English then Korean), `slides/` (the deck as 1920×1080 PNGs), `headline-table.md`, `mc-summary.json`. |
| `docs/KOREA_PRESET_EVIDENCE.md`, `docs/research/korea-fiscal-system.md` | Where every scenario input and every Korean fiscal parameter comes from. |

## Two ways to host it

**Static only.** Copy `web/dist/` to any static host. Every scenario preset, every policy
lever combination shipped as a preset, and their sensitivity charts are committed files
under `web/dist/data/korea/`. Custom slider values need the compute service; without it
the interactive page shows a banner saying so and keeps serving the presets. Nothing on
any page calls a host other than its own origin (fonts, map shapes and data are all
self-hosted).

**With the compute service.** Serve `web/dist/` and proxy `/api/` to the service on
`127.0.0.1:8000` — `deploy/nginx.conf.example` and `deploy/Caddyfile.example` do exactly
that; adapt the domain and root path. The service:

```bash
# Python 3.12 (uv shown; python -m venv works the same)
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r api/requirements.txt

# run (Korea-only mode: the US model is not loaded)
FISCAL_KOREA_ONLY=1 .venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
curl localhost:8000/api/health        # {"status":"ok","mode":"korea","korea_data":true,...}
```

`deploy/fiscal-api.service.example` is a systemd unit with the same command; set
`FISCAL_TORNADO_WORKERS` to cores minus two for parallel sensitivity draws. The first
request builds the Korea data pools (about a second); warm requests take tens of
milliseconds. Memory is well under 1 GB.

## Rebuilding the site

```bash
cd web && npm ci && npm run build      # -> web/dist
```

Node 20 or newer. The Vite config builds only the Korea entries. A rebuild does not
recreate `web/dist/index.html` (the packager writes that landing page); keep a copy or
link the four pages directly. The `web/src` tree also
contains the US app's modules, because the Korea pages import the chart, component and
copy modules they share; those files are type-checked but not built into any page.

All user-facing text lives in `web/src/content/copy.json` (English) and
`web/src/content/copy.ko.json` (Korean), under the `korea` key. Edit either and rebuild;
the language toggle and `?lang=ko` deep link switch between them.

## Regenerating the numbers

The data files under `web/public/data/korea/` are computed from the model and committed
so the site is static. If the model or a scenario changes, regenerate in this order,
then rebuild the site:

```bash
.venv/bin/python scripts/gen_korea_grid.py         # lever bounds and preset defaults
.venv/bin/python scripts/gen_korea_bundle.py       # the presenter page's bundle
.venv/bin/python scripts/gen_korea_scenarios.py    # ten scenario payloads + sensitivity charts
.venv/bin/python scripts/gen_korea_evidence_tables.py
.venv/bin/python scripts/korea_monte_carlo.py
.venv/bin/python -m pytest tests -q                # staleness tests fail if a bundle is out of date
```

The parsed tables in `data/raw/korea/*.tidy.csv` are rebuilt from the raw exports, without
network, by:

```bash
.venv/bin/python scripts/fetch_korea_tables.py --parse-only
.venv/bin/python scripts/fetch_korea_region_occupation.py --parse-only
```

`scripts/export_korea_slides.py` re-exports the deck PNGs (needs Google Chrome);
`scripts/gen_korea_about_pdf.py` re-renders the methodology PDF from the copy files.

## Health check and version

`GET /api/health` reports `mode` (`korea` when running in Korea-only mode), `korea_data`
(the parsed tables are present) and `version` (the `VERSION` file). Compare `version`
with the source commit after every deploy.
