"""Baseline comparison: refutation size with and without lrat-trim, for the certified substitution.
Usage: python3 ablation_trim.py <work_dir_with_prep.json> ... > out.json"""
import os, sys, json, glob, tempfile, subprocess
from common import load_bench, encode, write_cnf, hole_units, solve
from config import ROOT, LRATTRIM

def count(path):
    lem = hints = 0
    for line in open(path):
        t = line.split()
        if len(t) < 2 or t[1] == "d":
            continue
        z = t.index("0", 1); lem += 1; hints += len(t) - z - 2
    return lem, hints, os.path.getsize(path)

res = []
for w in sys.argv[1:]:
    pj = os.path.join(w, "prep.json")
    if not os.path.exists(pj):   # preparation did not finish (e.g. interrupted)
        continue
    pp = json.load(open(pj))
    if not pp.get("repair", {}).get("ok"):
        continue
    src = glob.glob(os.path.join(ROOT, "bench", "*", pp["name"] + ".c"))[0]
    b = load_bench(src); work = tempfile.mkdtemp(prefix="abl_")
    U = encode(b, "unsat", work); p = os.path.join(work, "u.cnf")
    write_cnf(p, U["nv"], U["clauses"], hole_units(U["holes"], pp["repair"]["sigma"]))
    rc, _ = solve(p, lrat=os.path.join(work, "p.lrat")); assert rc == 20
    subprocess.run([LRATTRIM, "--ascii", p, os.path.join(work, "p.lrat"), os.path.join(work, "t.lrat")], capture_output=True)
    l0, h0, s0 = count(os.path.join(work, "p.lrat")); l1, h1, s1 = count(os.path.join(work, "t.lrat"))
    res.append(dict(name=pp["name"], lemmas_raw=l0, hints_raw=h0, bytes_raw=s0, lemmas_trim=l1, hints_trim=h1, bytes_trim=s1))
    print(res[-1], file=sys.stderr)
print(json.dumps(res, indent=1))
