#!/bin/sh
# Rebuild everything from the raw-page cache ($0, ~10 s). Crawl first only for new pages:
#   python3 pipeline/crawl_fresha.py; python3 pipeline/crawl_booksy.py;
#   python3 pipeline/crawl_glossgenius.py; python3 pipeline/ownsite.py
set -e
cd "$(dirname "$0")/.."
python3 pipeline/load.py
python3 pipeline/map_services.py
python3 pipeline/benchmark.py
python3 scripts/check.py
python3 scripts/update_readme.py
