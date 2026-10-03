#!/usr/bin/env bash
# Packs results/ and the small per-benchmark records (no keys, circuits, or witnesses) into results_bundle.tgz.
cd "$(dirname "$0")"; W="${ZKAPR_WORK:-$PWD/work}"
{ uname -a; lscpu | grep -E "Model name|^CPU\(s\)"; free -g | head -2; lsb_release -d 2>/dev/null; } > results/platform.txt
FILES=$(cd "$W" && ls -d */prep.json */prove.json */timing.json */prep.log */prove.log */timing.log 2>/dev/null)
tar czf results_bundle.tgz results -C "$W" $FILES
ls -la results_bundle.tgz
