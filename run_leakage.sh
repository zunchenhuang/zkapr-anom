#!/usr/bin/env bash
# RQ3: sample correct fixes per benchmark and measure the leakage of the padded sizes.
cd "$(dirname "$0")"; mkdir -p results/leakage
for n in m1_parity m2_clamp m5_offset m4_threshold; do
  (cd pipeline && python3 leakage.py ../bench/micro/$n.c 25 ../results/leakage/$n.json)
done
