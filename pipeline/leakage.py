"""RQ6: how much does the leakage L(sigma) (padded refutation sizes) reveal?
For a benchmark, sample many correct substitutions, compute L for each, and report
the number of distinct classes and the min-entropy of the class given a uniform correct sigma.
Usage: python3 leakage.py <bench.c> <n_samples> <out.json>"""
import sys, os, json, random, math, tempfile, collections
from common import load_bench, encode, write_cnf, hole_units, solve
from witness import build

SAMPLERS = {
    "m1_parity": lambda rnd: [rnd.randrange(0, 1 << 32, 2), rnd.randrange(0, 1 << 32, 2)],
    "m2_clamp": lambda rnd: [rnd.randrange(10, 1 << 31), rnd.randrange(10, 51)],
    "m5_offset": lambda rnd: (lambda a: [a, (a - 3) % (1 << 32)])(rnd.randrange(0, 1 << 32)),
    "m4_threshold": lambda rnd: [rnd.randrange(500, 1 << 32)],
}


def correct(b, work, sigma, U):
    p = os.path.join(work, "lk.cnf"); write_cnf(p, U["nv"], U["clauses"], hole_units(U["holes"], sigma))
    return solve(p)[0] == 20


def main(path, n, out):
    b = load_bench(path); rnd = random.Random(2027)
    work = tempfile.mkdtemp(prefix="leak_"); U = encode(b, "unsat", work)
    rows, tries = [], 0
    while len(rows) < n and tries < 20 * n:
        tries += 1
        s = SAMPLERS[b["name"]](rnd)
        if not correct(b, work, s, U):
            continue
        _, m, _ = build(b, work, s)
        rows.append(dict(sigma=s, NL=m["NL"], TT=m["TT"], TD=m["TD"], Q=m["Q"], T=m["T"], nL=m["nL"]))
        print(b["name"], s, (m["NL"], m["TT"], m["TD"], m["Q"]), "raw T", m["T"], flush=True)
    cls = collections.Counter((r["NL"], r["TT"], r["TD"], r["Q"]) for r in rows)
    raw = collections.Counter(r["T"] for r in rows)
    top = max(cls.values()) / len(rows)
    res = dict(name=b["name"], samples=len(rows), classes=len(cls), raw_T_values=len(raw),
               largest_class_share=top, min_entropy_bits=-math.log2(top), rows=rows)
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
