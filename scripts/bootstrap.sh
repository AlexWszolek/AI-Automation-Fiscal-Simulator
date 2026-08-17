#!/usr/bin/env bash
# Bootstrap the AI Automation Fiscal Model from a fresh clone: build the Python 3.12 env
# and the (gitignored, regenerable) interim artifacts the model and app depend on.
#
#   bash scripts/bootstrap.sh
#
# Idempotent — skips steps whose outputs already exist.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 1/7  Python 3.12 venv (via uv)"
command -v uv >/dev/null 2>&1 || python3 -m pip install -q uv
[ -d .venv ] || uv venv --python 3.12 .venv

echo "==> 2/7  core deps (model + app + tests)"
uv pip install --python .venv/bin/python -q -r requirements.txt

echo "==> 3/7  ACS PUMS household microdata (csv_hus.zip ~251MB) for the NOC build"
if [ ! -f data/external/pums_hus/psam_husa.csv ]; then
  mkdir -p data/external
  curl -L --fail -sS -o data/external/csv_hus.zip \
    "https://www2.census.gov/programs-surveys/acs/data/pums/2024/1-Year/csv_hus.zip"
  (cd data/external && unzip -o -q csv_hus.zip -d pums_hus)
else
  echo "    (already present)"
fi

echo "==> 4/7  NOC distribution (Part A) -> data/interim/noc_distribution.csv"
.venv/bin/python -m fiscal_model.noc

echo "==> 5/7  PolicyEngine benefit bake (Part B, heavy) -> data/interim/benefit_lookup.parquet"
uv pip install --python .venv/bin/python -q -r requirements-bake.txt
.venv/bin/python scripts/bake_benefits.py

echo "==> 6/7  per-worker delta precompute (dynamics cache)"
.venv/bin/python -m fiscal_model.dynamics >/dev/null

echo "==> 7/7  Korea tidy tables (from committed raw exports)"
if [ ! -f data/raw/korea/DT_118N_PAYM39.tidy.csv ] || [ ! -f data/raw/korea/region_occupation.tidy.csv ]; then
  .venv/bin/python scripts/fetch_korea_tables.py --parse-only
  .venv/bin/python scripts/fetch_korea_region_occupation.py --parse-only
else
  echo "    (already present)"
fi

echo
echo "Done. Run the tests:    .venv/bin/python -m pytest -q"
echo "      Headline scenario: .venv/bin/python -m fiscal_model.dynamics"
echo "      The site (dev):    cd web && npm install && npm run dev"
echo "                         .venv/bin/uvicorn api.main:app --port 8000"
