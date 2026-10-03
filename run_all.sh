#!/usr/bin/env bash
# Full evaluation: all 20 benchmarks (hand-written, SV-COMP, IntroClass), the trimming baseline,
# the repair walk-through, the leakage experiment (RQ3), and the D-scaling probe; then results/ and
# results_bundle.tgz.  Environment: PREP_JOBS (parallel preparation, default 3), PREP_TIMEOUT and
# PROVE_TIMEOUT (per benchmark, default 3h and 4h), BENCH (space-separated subset, default all).
set -u
cd "$(dirname "$0")"; ROOT="$PWD"
export ZKAPR_WORK="${ZKAPR_WORK:-$ROOT/work}"; mkdir -p "$ZKAPR_WORK" results
PREP_JOBS="${PREP_JOBS:-3}"; PREP_TIMEOUT="${PREP_TIMEOUT:-3h}"; PROVE_TIMEOUT="${PROVE_TIMEOUT:-4h}"
ALL=$(ls bench/micro/m*.c bench/sv/sv*.c bench/introclass/ic_*.c)
[ -n "${BENCH:-}" ] && ALL=$(for n in $BENCH; do ls bench/*/$n.c; done)
log() { echo "[$(date +%T)] $*" | tee -a results/run_all.log; }
FREE_GB=$(df -Pk "$ZKAPR_WORK" | awk 'NR==2 {print int($4/1048576)}')
[ "$FREE_GB" -lt 40 ] && log "WARNING: only ${FREE_GB} GB free in $ZKAPR_WORK; about 40 GB are recommended"

log "phase 1: repair, certificate, circuit (parallel, $PREP_JOBS jobs)"
prep_one() {
  b="$1"; n=$(basename "$b" .c); w="$ZKAPR_WORK/$n"; mkdir -p "$w"
  if grep -q '"compile_ok": true' "$w/prep.json" 2>/dev/null; then echo "[$n] prepared (cached)"; return; fi
  (cd pipeline && timeout "$PREP_TIMEOUT" python3 prep.py "$ROOT/$b" "$w" > "$w/prep.log" 2>&1) \
    && echo "[$n] prepared" || echo "[$n] preparation FAILED (see $w/prep.log)"
}
export -f prep_one; export ROOT PREP_TIMEOUT
echo "$ALL" | xargs -P "$PREP_JOBS" -I{} bash -c 'prep_one {}' | tee -a results/run_all.log

log "phase 2: setup, CRS check, proving, verification, attacks, timing (sequential)"
for b in $ALL; do
  n=$(basename "$b" .c); w="$ZKAPR_WORK/$n"
  grep -q '"compile_ok": true' "$w/prep.json" 2>/dev/null || { log "[$n] skipped (not prepared)"; continue; }
  if ! grep -q '"verify_ok": true' "$w/prove.json" 2>/dev/null; then
    (cd pipeline && timeout "$PROVE_TIMEOUT" python3 prove.py "$w" > "$w/prove.log" 2>&1) || log "[$n] proving FAILED (see $w/prove.log)"
  fi
  if grep -q '"verify_ok": true' "$w/prove.json" 2>/dev/null && [ ! -f "$w/timing.json" ]; then
    (cd pipeline && python3 timing.py "$n" > "$w/timing.log" 2>&1) || log "[$n] timing pass FAILED"
  fi
  # proving keys are large and not needed afterwards (vk, proof, and public input are kept)
  [ "${KEEP_KEYS:-0}" = 1 ] || rm -f "$w"/pk*.bin "$w"/aux*.bin
  log "[$n] done"
done

log "phase 3: baseline, walk-through, leakage, D-scaling"
(cd pipeline && python3 ablation_trim.py $(ls -d "$ZKAPR_WORK"/*/) > ../results/ablation_trim.json 2> ../results/ablation_trim.log)
(cd pipeline && python3 cegis_trace.py ../bench/introclass/ic_median_3.c ../results/trace_ic_median_3.json > /dev/null)
./run_leakage.sh > results/leakage.log 2>&1
rm -f results/dscaling.json
(cd pipeline && python3 dprobe.py ../bench/sv/sv2_count_up_down.c 2 3 4 6 --json ../results/dscaling.json \
              && python3 dprobe.py ../bench/sv/sv3_gsv2008.c 3 4 6 --json ../results/dscaling.json) > results/dscaling.log 2>&1

log "phase 4: tables, numbers, figure"
(cd pipeline && python3 report.py > ../results/report.log 2>&1 && python3 make_numbers.py >> ../results/report.log 2>&1 && python3 make_figure.py >> ../results/report.log 2>&1)
./pack_results.sh
if [ -s results/numbers.tex ]; then log "finished; send results_bundle.tgz"
else log "report FAILED (see results/report.log); results_bundle.tgz contains the logs for diagnosis"; fi
