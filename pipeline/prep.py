"""Prepare one benchmark up to a compiled circuit + witness input.
Usage: python3 prep.py <bench.c> <workdir>"""
import sys, os, json, time, subprocess
from common import *
from cegis import cegis
from witness import build
from gencircuit import gen

from config import CIRCOM, CIRCOMLIB as LIB


def cbmc_verdict(b, work, kind, sigma):
    """CBMC's own verdict on the directly patched program: 10 = property fails, 20 = holds."""
    cfile = os.path.join(work, "h_%s_v.c" % kind)
    open(cfile, "w").write(harness(b, kind, sigma=sigma))
    r = subprocess.run([CBMC, cfile, "--unwind", str(b["D"]), "--no-unwinding-assertions"],
                       capture_output=True, text=True)
    if "VERIFICATION SUCCESSFUL" in r.stdout:
        return 20
    if "VERIFICATION FAILED" in r.stdout:
        return 10
    raise RuntimeError(r.stdout[-400:])


def bridge(b, work, sigma):
    """Assumption 2 (as equisatisfiability): Psi[sigma] vs the directly encoded P_b[L->sigma]."""
    res = {}
    for kind, direct in (("unsat", "direct"), ("sat", "direct_sat")):
        E = encode(b, kind, work)
        p1 = os.path.join(work, "br_sub_%s.cnf" % kind)
        write_cnf(p1, E["nv"], E["clauses"], hole_units(E["holes"], sigma))
        r1, _ = solve(p1)
        res[kind] = (r1, cbmc_verdict(b, work, direct, sigma))
    ok = all(a == c for (a, c) in res.values())
    return ok, res


if __name__ == "__main__":
    b = load_bench(sys.argv[1]); work = sys.argv[2]
    os.makedirs(work, exist_ok=True)
    out = dict(name=b["name"], bin=b["BIN"], K=b["K"], D=b["D"], orig=b["ORIG"])
    # vendor: repair
    rep = cegis(b, work)
    out["repair"] = rep
    if not rep["ok"]:
        json.dump(out, open(os.path.join(work, "prep.json"), "w"), indent=1); sys.exit(1)
    sigma = rep["sigma"]
    # buggy program really buggy? (sanity)
    U = encode(b, "unsat", work)
    pbug = os.path.join(work, "bug.cnf"); write_cnf(pbug, U["nv"], U["clauses"], hole_units(U["holes"], b["ORIG"]))
    out["orig_violates"] = solve(pbug)[0] == 10
    # customer-side instance computation time (encoding only, no solving)
    t0 = time.time(); encode(b, "unsat", work); encode(b, "sat", work); out["t_inst_encode"] = time.time() - t0
    ok, br = bridge(b, work, sigma)
    out["bridge_ok"], out["bridge"] = ok, br
    if b["REF"]:
        okr, _ = bridge(b, work, b["REF"]); out["bridge_ref_ok"] = okr
    # vendor: witness
    inp, meta, consts = build(b, work, sigma)
    out["meta"] = meta
    inp["c"] = None
    json.dump(dict(inp=inp, meta=meta), open(os.path.join(work, "witness_raw.json"), "w"))
    info = gen(meta, consts, os.path.join(work, "main.circom"))
    out["circuit"] = info
    # compile (instance-specific circuit; both parties can regenerate it from public data)
    t0 = time.time()
    # --O2 simplifies constraints but needs much memory; fall back to --O1 if it fails
    for opt in (os.environ.get("ZKAPR_CIRCOM_OPT", "--O2"), "--O1"):
        r = subprocess.run([CIRCOM, "main.circom", "--r1cs", "--wasm", opt, "-l", LIB, "-o", "."],
                           cwd=work, capture_output=True, text=True)
        out["circom_opt"] = opt
        if r.returncode == 0:
            break
    out["t_compile"] = time.time() - t0
    out["compile_ok"] = r.returncode == 0
    m = re.search(r"non-linear constraints:\s*(\d+)", r.stdout)
    m2 = re.search(r"linear constraints:\s*(\d+)", r.stdout.split("non-linear")[-1])
    out["r1cs_nonlinear"] = int(m.group(1)) if m else None
    out["r1cs_linear"] = int(m2.group(1)) if m2 else None
    if r.returncode != 0:
        out["compile_err"] = (r.stdout + r.stderr)[-3000:]
    json.dump(out, open(os.path.join(work, "prep.json"), "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("name", "bridge_ok", "orig_violates", "t_compile", "compile_ok", "r1cs_nonlinear", "r1cs_linear")}))
    print(json.dumps(meta))
    if not out["compile_ok"]:
        print(out["compile_err"])
