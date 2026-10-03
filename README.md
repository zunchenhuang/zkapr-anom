# ZKA-PR artifact: Zero-Knowledge Argument for Program Repair

This artifact reproduces the evaluation of the paper (Section 8): every number and data table in
the paper is generated from the measurements by `pipeline/report.py` and `pipeline/make_numbers.py`.

A vendor repairs a buggy C program and proves in zero knowledge that a committed,
hidden substitution sigma for the declared holes makes the program free of violations
within a bound D. The customer verifies a 128-byte Groth16 proof.

```

## Requirements

Linux x86_64 (Ubuntu 20.04 or later) or macOS; git, make, a C compiler, curl,
Python >= 3.8 with numpy and matplotlib, Node.js >= 16 with npm, and Rust >= 1.75
(https://rustup.rs). No root access is needed: when the system CBMC is missing or older than 5.95,
`setup.sh` unpacks the pinned CBMC 5.95.1 package into `tools/`, and when the Circom release binary
does not run (it needs glibc >= 2.34), `setup.sh` builds Circom 2.2.2 from source, which produces
byte-identical circuits.

## Setup (about 10 minutes)

```
./setup.sh
```

This installs into `./tools`: CaDiCaL and lrat-trim (pinned commits), Circom 2.2.2,
circomlib/circomlibjs, and builds the prover in `prover/` (`cargo build --release`).
`prover/Cargo.lock` is pinned so that rustc 1.75 and newer both build it.

All tool paths can be overridden with environment variables
(`CBMC`, `CADICAL`, `LRATTRIM`, `CIRCOM`, `NODE_MODULES`, `ZKP`, `ZKAPR_TOOLS`,
`ZKAPR_WORK`, `ZKAPR_RESULTS`); see `pipeline/config.py`.

## Quick check (about 3 minutes)

```
./run_one.sh bench/sv/sv6_css2003.c
(cd pipeline && python3 report.py)
```

Expected: the CRS check accepts the honest CRS, the benchmark is certified, all tampering tests
report `true` (rejected), about 61k constraints, verification of a few milliseconds, and a
128-byte proof.

## Individual experiments

```
./run_one.sh bench/introclass/ic_median_3.c   # one benchmark: prepare, prove, attacks, timing
./run_dscaling.sh     # refutation size versus D (RQ2), seconds per point
./run_leakage.sh      # leakage of the padded sizes over 25 correct fixes per benchmark (RQ3)
```

## Full evaluation on a workstation (recommended: 32 GB RAM)

```
./setup.sh                      # once: CBMC, CaDiCaL, lrat-trim, Circom, circomlib, the Rust prover
./run_all.sh                    # everything; resumable (finished benchmarks are skipped)
```

Phase 1 prepares benchmarks in parallel (repair, certificate, circuit compilation; `PREP_JOBS=3` by
default, about 3-8 GB each). Phase 2 proves and times them one at a time, so timings are not
contended. Phase 3 runs the trimming baseline, the repair walk-through, the leakage experiment, and
the D-scaling probe; phase 4 writes `results/` and packs `results_bundle.tgz` (a few MB: results plus
the small per-benchmark records and logs, no keys or circuits). Expect several hours on a 6-core
desktop; `ic_smallest_2` (about 18k hint steps) may exceed `PREP_TIMEOUT` (default 3h) and is then
reported as uncertified. Disk: about 40 GB free (circuits are kept, proving keys are deleted after
each benchmark unless `KEEP_KEYS=1`). A subset can be run with `BENCH="ic_median_1 ic_grade_2" ./run_all.sh`.


## Verifiable CRS (prover/src/crs.rs)

`zkp setup2` (customer) generates the Groth16 key plus auxiliary elements
P^{tau^k} (k < n), Q, Q^tau, Q^{tau^n}, Q^alpha. `zkp crscheck` (vendor) checks, with batched pairing
equations and private randomness, that every element is consistent with one nonzero trapdoor, and that
every G2 element is in the prime-order subgroup (paper, Figure "CRS check"). `zkp subvert <mode>`
produces the subverted keys used in attack T7 (modes: h, l, alpha, gamma0, a).

## Tampering tests (RQ1)

T1 buggy substitution with the fix's refutation; T3 negated lemma literal; T3b inflated lookup
multiplicity; T6 corrupted model; T2 proof against the buggy commitment; T2b proof under another
instance's verification key; T5 bit flips in the proof; T4 wrong opening of the commitment;
T7 five CRS subversions, each of which the vendor's CRS check must reject.
