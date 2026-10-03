"""Log every iteration of the vendor's repair loop (paper: repair walk-through figure).
Usage: python3 cegis_trace.py <bench.c> <out.json>"""
import os, sys, json, tempfile
from common import load_bench, encode, write_cnf, hole_units, solve, bits_value

def main(path, out):
    b = load_bench(path); work = tempfile.mkdtemp(prefix="trace_")
    U = encode(b, "unsat", work)
    sigma, cexs, log = list(b["ORIG"]), [], []
    for it in range(1, 201):
        p = os.path.join(work, "v.cnf"); write_cnf(p, U["nv"], U["clauses"], hole_units(U["holes"], sigma))
        rc, model = solve(p)
        if rc == 20:
            log.append(dict(iter=it, candidate=sigma, verdict="UNSAT")); break
        x = [bits_value(l, model) if l else 0 for l in U["ins"]]
        log.append(dict(iter=it, candidate=sigma, verdict="SAT", counterexample=x))
        cexs.append(x)
        S = encode(b, "synth", work, cexs=cexs); p = os.path.join(work, "s.cnf")
        write_cnf(p, S["nv"], S["clauses"]); rc, model = solve(p)
        sigma = [bits_value(l, model) for l in S["holes"]]
    json.dump(dict(name=b["name"], psi_clauses=len(U["clauses"]), log=log), open(out, "w"), indent=1)
    for e in log: print(e)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
