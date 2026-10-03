import sys, re, os, json, tempfile
from common import load_bench
from cegis import cegis
from witness import build
args = sys.argv[1:]
out = None
if "--json" in args:
    i = args.index("--json"); out = args[i + 1]; del args[i:i + 2]
src = args[0]; pts = []
for D in map(int, args[1:]):
    t = open(src).read(); t = re.sub(r"// D: \d+", "// D: %d" % D, t)
    p = os.path.join(tempfile.gettempdir(), "dp_%d.c" % D); open(p, "w").write(t)
    b = load_bench(p); w = os.path.join(tempfile.gettempdir(), "dpw_%s_%d" % (os.path.basename(src), D))
    r = cegis(b, w)
    if not r["ok"]: print(D, "repair failed"); continue
    try:
        _, m, _ = build(b, w, r["sigma"])
        print(os.path.basename(src), "D=%d" % D, "sigma", r["sigma"], "nB", m["nB"], "nL", m["nL"], "T", m["T"], flush=True)
        pts.append(dict(D=D, psi_clauses=m["nB"], lemmas=m["nL"], hint_steps=m["T"]))
    except Exception as e:
        print(D, "witness error", e)

if out:
    d = json.load(open(out)) if os.path.exists(out) else {}
    d[os.path.basename(src)[:-2]] = pts
    json.dump(d, open(out, "w"), indent=1)
