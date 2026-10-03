"""Vendor repair loop (outside the trusted base): CEGIS over the sketch encoding."""
import os, time, json, sys
from common import *


def cegis(b, work, max_iter=200, timeout=1800):
    t0 = time.time()
    U = encode(b, "unsat", work)
    sigma = list(b["ORIG"])
    cexs, it, solver_calls = [], 0, 0
    while True:
        it += 1
        if it > max_iter or time.time() - t0 > timeout:
            return dict(ok=False, iters=it, time=time.time() - t0)
        # verify candidate: Psi[sigma] /\ not Phi
        path = os.path.join(work, "cegis_v.cnf")
        write_cnf(path, U["nv"], U["clauses"], hole_units(U["holes"], sigma))
        rc, model = solve(path); solver_calls += 1
        if rc == 20:
            return dict(ok=True, sigma=sigma, iters=it, cexs=len(cexs),
                        solver_calls=solver_calls, time=time.time() - t0)
        x = [bits_value(lits, model) if lits else 0 for lits in U["ins"]]
        cexs.append(x)
        # synthesize: exists H. forall collected x_j: prog(H, x_j) ok
        S = encode(b, "synth", work, cexs=cexs)
        path = os.path.join(work, "cegis_s.cnf")
        write_cnf(path, S["nv"], S["clauses"])
        rc, model = solve(path); solver_calls += 1
        if rc != 10:
            return dict(ok=False, reason="no candidate", iters=it, time=time.time() - t0)
        sigma = [bits_value(l, model) for l in S["holes"]]


if __name__ == "__main__":
    b = load_bench(sys.argv[1]); work = sys.argv[2]
    res = cegis(b, work)
    json.dump(res, open(os.path.join(work, "cegis.json"), "w"))
    print(json.dumps(res))
