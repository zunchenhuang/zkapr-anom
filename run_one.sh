#!/usr/bin/env bash
# Usage: ./run_one.sh bench/sv/sv6_css2003.c
# Repair, bridge check, witness, circuit, compile, setup, prove, verify, tampering tests, quiet timing.
set -euo pipefail
cd "$(dirname "$0")"; ROOT="$PWD"; B="$1"; N="$(basename "$B" .c)"
W="${ZKAPR_WORK:-$ROOT/work}/$N"; mkdir -p "$W"
cd pipeline
echo "[$N] prepare";  python3 prep.py "$ROOT/$B" "$W"
echo "[$N] prove";    python3 prove.py "$W"
echo "[$N] timing";   rm -f "$W/timing.json"; python3 timing.py "$N"
