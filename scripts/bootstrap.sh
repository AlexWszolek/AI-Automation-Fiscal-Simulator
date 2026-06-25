#!/usr/bin/env bash
# Bootstrap the AI Automation Fiscal Model from a fresh clone: build the Python 3.12 env
# and the (gitignored, regenerable) interim artifacts the model and app depend on.
#
#   bash scripts/bootstrap.sh
#
# Idempotent — skips steps whose outputs already exist.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 1/6  Python 3.12 venv (via uv)"
command -v uv >/dev/null 2>&1 || python3 -m pip install -q uv
[ -d .venv ] || uv venv --python 3.12 .venv

echo "==> 2/6  core deps (model + app + tests)"
uv pip install --python .venv/bin/python -q -r requirements.txt

echo "==> 3/6  ACS PUMS household microdata (csv_hus.zip ~251MB) for the NOC build"
if [ ! -f data/external/pums_hus/psam_husa.csv ]; then
  mkdir -p data/external
  curl -L --fail -sS -o data/external/csv_hus.zip \
    "https://www2.census.gov/programs-surveys/acs/data/pums/2024/1-Year/csv_hus.zip"
  (cd data/external && unzip -o -q csv_hus.zip -d pums_hus)
else
  echo "    (already present)"
fi

echo "==> 4/6  NOC distribution (Part A) -> data/interim/noc_distribution.csv"
.venv/bin/python -m fiscal_model.noc

echo "==> 5/6  PolicyEngine benefit bake (Part B, heavy) -> data/interim/benefit_lookup.parquet"
uv pip install --python .venv/bin/python -q -r requirements-bake.txt
.venv/bin/python scripts/bake_benefits.py

echo "==> 6/6  per-worker delta precompute (dynamics cache)"
.venv/bin/python -m fiscal_model.dynamics >/dev/null

echo
echo "Done. Run the app:   .venv/bin/streamlit run app/streamlit_app.py"
echo "      Run the tests: .venv/bin/python -m pytest -q"
