#!/usr/bin/env bash
# RQ2: refutation size versus D (no proving). Writes results/dscaling.json.
cd "$(dirname "$0")/pipeline"; rm -f ../results/dscaling.json
python3 dprobe.py ../bench/sv/sv2_count_up_down.c 2 3 4 6 --json ../results/dscaling.json
python3 dprobe.py ../bench/sv/sv3_gsv2008.c 3 4 6 --json ../results/dscaling.json
