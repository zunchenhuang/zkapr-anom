"""Emit numbers.tex (every evaluation number quoted in the paper) and dscaling_rows.tex,
computed from results.json, the benchmark headers, and dscaling.json.
Usage: python3 make_numbers.py [results_dir] [dscaling.json]"""
import json, os, sys, glob, math, collections, statistics as st
from config import RESULTS, ROOT
from common import load_bench

WORDS = "Zero One Two Three Four Five Six Seven Eight Nine".split()
def mname(k):
    return "".join(WORDS[int(ch)] if ch.isdigit() else ch for ch in k if ch.isalnum())

rd = sys.argv[1] if len(sys.argv) > 1 else RESULTS
ds = sys.argv[2] if len(sys.argv) > 2 else os.path.join(rd, "dscaling.json")
r = json.load(open(os.path.join(rd, "results.json")))
EXCLUDE = set(json.load(open(os.path.join(ROOT, "bench", "descriptions.json"))).get("_paper_exclude", []))
r = [x for x in r if x["name"] not in EXCLUDE]   # benchmarks kept in the artifact but outside the paper's scope
N = {}
def put(k, v, fmt="%s"): N[k] = fmt % v
def rng(key, lab, fmt, scale=1.0):
    xs = [x[key] * scale for x in r if x.get(key) is not None]
    if not xs:
        return
    put(lab + "Med", st.median(xs), fmt); put(lab + "Min", min(xs), fmt); put(lab + "Max", max(xs), fmt)

GROUPS = (("m", "Hand-written programs"), ("sv", "SV-COMP programs"), ("ic", "IntroClass programs (real bugs, student fixes)"))
def grp(name): return "ic" if name.startswith("ic_") else ("m" if name.startswith("m") else "sv")
desc = json.load(open(os.path.join(ROOT, "bench", "descriptions.json")))
CMPS = ["$<$", "$\\leq$", "$>$", "$\\geq$", "$=$", "$\\neq$", "$<$", "$\\leq$"]
def decode(name, vals):
    d = desc.get(name)
    if not d or len(d) < 4: return None
    out = []
    for kind, v in zip(d[3], vals):
        if kind == "cmp": out.append(CMPS[v & 7])
        elif kind.startswith("sel5:"): vs = kind[5:].split(","); out.append("\\texttt{%s}" % vs[min(v & 7, 4)])
        elif kind.startswith("sel:"): vs = kind[4:].split(","); out.append("\\texttt{%s}" % vs[min(v & 3, 2)])
        else: out.append(str(v))
    return out
_all = [os.path.basename(f)[:-2] for f in glob.glob(os.path.join(ROOT, "bench", "*", "*.c")) if not os.path.basename(f).startswith("_")]
_all = [n for n in _all if n not in EXCLUDE]
put("nCert", len(r)); put("nBugs", len(_all))
for key, lab, fmt, sc in (("t_rep", "rep", "%.2f", 1), ("t_wtns", "wit", "%.1f", 1), ("t_prove", "prove", "%.1f", 1),
                          ("t_setup", "setup", "%.1f", 1), ("t_crscheck", "chk", "%.1f", 1), ("t_verify_ms", "ver", "%.2f", 1),
                          ("mem_prove_mb", "mem", "%.0f", 1), ("r", "", "", 1)):
    if key != "r":
        rng(key, lab, fmt, sc)
rng("r1cs", "kcons", "%.0f", 1e-3); rng("hint_steps", "steps", "%.0f"); rng("pk_mb", "pk", "%.0f"); rng("aux_mb", "aux", "%.1f")
tam = [k for k in r[0] if k.startswith("tam_")]
per = {"tam_T7_subverted_crs": 5}
put("nAttacks", len(tam)); put("nClaims", sum(per.get(k, 1) for k in tam) * len(r))
put("allRejected", "all" if all(all(x[k] for k in tam if x.get(k) is not None) for x in r) else "NOT ALL")
ratio = [(x["t_prove"] + x["t_setup"] + (x.get("t_crscheck") or 0)) / x["t_rep"] for x in r]
put("ratioMed", st.median(ratio), "%.0f"); put("ratioMin", min(ratio), "%.0f"); put("ratioMax", max(ratio), "%.0f")
if any(x.get("t_crscheck") for x in r):
    put("chkOverSetup", st.median([x["t_crscheck"] / x["t_setup"] for x in r if x.get("t_crscheck")]), "%.1f")
    put("chkUsPerC", st.median([x["t_crscheck"] / x["r1cs"] * 1e6 for x in r if x.get("t_crscheck")]), "%.0f")
import numpy as np
s = np.array([x["hint_steps"] for x in r], float); c = np.array([x["r1cs"] for x in r], float); n = np.array([x["psi_clauses"] for x in r], float)
q = np.array([x["Q"] for x in r], float)
A = np.vstack([s * q, s, n, np.ones_like(s)]).T; coef, *_ = np.linalg.lstsq(A, c, rcond=None); pred = A @ coef
put("perSlot", coef[0], "%.0f"); put("perStep", coef[1], "%.0f"); put("perClause", coef[2], "%.0f")
put("fitRsq", 1 - ((c - pred) ** 2).sum() / ((c - c.mean()) ** 2).sum(), "%.2f")
A2 = np.vstack([s, n, np.ones_like(s)]).T; c2, *_ = np.linalg.lstsq(A2, c, rcond=None); p2 = A2 @ c2
put("fitRsqStepsOnly", 1 - ((c - p2) ** 2).sum() / ((c - c.mean()) ** 2).sum(), "%.2f")
put("corrSteps", np.corrcoef(s, c)[0, 1] if len(r) > 2 else float("nan"), "%.2f")
put("corrStepsQ", np.corrcoef(s * q, c)[0, 1] if len(r) > 2 else float("nan"), "%.2f")
put("corrPsi", np.corrcoef(n, c)[0, 1] if len(r) > 2 else float("nan"), "%.2f")
put("qMax", int(q.max())); put("qMin", int(q.min()))
put("proveUsPerC", st.median([x["t_prove"] / x["r1cs"] * 1e6 for x in r]), "%.0f")
put("setupUsPerC", st.median([x["t_setup"] / x["r1cs"] * 1e6 for x in r]), "%.0f")
put("nEncChecks", 4 * len(r)); put("encAll", "all" if all(x["bridge_ok"] and x["bridge_ref_ok"] for x in r) else "NOT ALL")
refs = {}
for f in glob.glob(os.path.join(ROOT, "bench", "*", "[ms]*.c")) + glob.glob(os.path.join(ROOT, "bench", "introclass", "ic_*.c")):
    b = load_bench(f); refs[b["name"]] = b["REF"]
def same(x):
    f = [int(v) for v in x["sigma"].split()]; ref = refs.get(x["name"])
    dd = decode(x["name"], f)
    return (dd == decode(x["name"], ref)) if dd is not None else (f == ref)
put("nDiffRef", sum(1 for x in r if not same(x) and grp(x["name"]) != "ic")); put("nNonIC", sum(1 for x in r if grp(x["name"]) != "ic"))
put("nIC", sum(1 for x in r if grp(x["name"]) == "ic")); put("nICbugs", sum(1 for n in _all if n.startswith("ic_"))); put("nICsame", sum(1 for x in r if grp(x["name"]) == "ic" and same(x)))
for key, lab in (("share_range", "shareRange"), ("share_fs_hash", "shareHash"), ("share_refutation", "shareRup"),
                 ("share_model", "shareModel"), ("share_clause_table", "shareTable")):
    xs = [100 * x[key] for x in r]; put(lab + "Min", min(xs), "%.0f"); put(lab + "Max", max(xs), "%.0f")

# compile time (minutes) and fix-quality rows
ct = [x["t_compile"] / 60 for x in r]
put("compMin", min(ct), "%.1f"); put("compMax", max(ct), "%.1f")
def fmt(v):
    v = int(v)
    return "\\texttt{0x%08x}" % v if v >= 1 << 24 else str(v)
fx = []
for g, lab in GROUPS:
    rows_g = [x for x in r if grp(x["name"]) == g]
    if not rows_g or g != "ic": continue
    for x in sorted(rows_g, key=lambda z: z["name"]):
        found = [int(v) for v in x["sigma"].split()]; ref = refs.get(x["name"]) or []; orig = [int(v) for v in x["orig"].split()]
        show = (lambda vs: ", ".join(decode(x["name"], vs))) if decode(x["name"], found) is not None else (lambda vs: ", ".join(map(fmt, vs)))
        fx.append("%s & %s & %s & %s & %s \\\\" % (x["name"].replace("_", "\\_"), show(orig), show(found), show(ref), "\\yes" if same(x) else "\\no"))
open(os.path.join(rd, "fixes_rows.tex"), "w").write("\n".join(fx) + "\n")

# RQ6 leakage rows (from leakage.py outputs in <results>/leakage/*.json)
ld = os.path.join(rd, "leakage")
lrows = []
if os.path.isdir(ld):
    for f in sorted(glob.glob(os.path.join(ld, "*.json"))):
        L = json.load(open(f))
        p2 = lambda v: 1 << max(0, (int(v) - 1).bit_length())
        c2 = collections.Counter()
        for x in L["rows"]:
            NL2 = p2(x["nL"] + 1); c2[(NL2, p2(x["T"] + NL2 - x["nL"]), p2(x["TD"]), x["Q"])] += 1
        top2 = max(c2.values()) / L["samples"]
        L["classes_pow2"], L["bits_pow2"] = len(c2), -math.log2(top2)
        lrows.append("%s & %d & %d & %d & %.2f & %d & %.2f \\\\" % (L["name"].replace("_", "\\_"), L["samples"], L["raw_T_values"],
                     L["classes"], abs(L["min_entropy_bits"]), L["classes_pow2"], abs(L["bits_pow2"])))
    if lrows:
        allL = [json.load(open(f)) for f in glob.glob(os.path.join(ld, "*.json"))]
        put("leakMaxBits", max(abs(L["min_entropy_bits"]) for L in allL), "%.2f")
        put("leakMaxClasses", max(L["classes"] for L in allL))
        p2c = []
        for L in allL:
            p2 = lambda v: 1 << max(0, (int(v) - 1).bit_length()); c2 = collections.Counter()
            for x in L["rows"]:
                NL2 = p2(x["nL"] + 1); c2[(NL2, p2(x["T"] + NL2 - x["nL"]), p2(x["TD"]), x["Q"])] += 1
            p2c.append(-math.log2(max(c2.values()) / L["samples"]))
        put("leakMaxBitsPow", abs(max(p2c)), "%.2f")
        put("leakSamples", allL[0]["samples"]); put("leakBenches", len(allL))
open(os.path.join(rd, "leak_rows.tex"), "w").write("\n".join(lrows) + "\n")

# Table 2 (benchmark statistics) and Table 3 (results with the untrimmed baseline)
desc = json.load(open(os.path.join(ROOT, "bench", "descriptions.json")))
t2 = []
for sub, lab in (("micro", "Hand-written programs"), ("sv", "SV-COMP programs (ReachSafety)"), ("introclass", "IntroClass programs (real bugs)")):
    t2.append("\\rowgroup{6}{%s}" % lab)
    for f in sorted(glob.glob(os.path.join(ROOT, "bench", sub, "*.c"))):
        if os.path.basename(f)[:-2] in EXCLUDE:
            continue
        b = load_bench(f); src = open(f).read().splitlines()
        loc = desc[b["name"]][2] if len(desc[b["name"]]) > 2 else sum(1 for l in src if l.strip() and not l.strip().startswith("//"))
        mut = sum(1 for o, q in zip(b["ORIG"], b["REF"]) if o != q)
        t2.append("%s & %d & %s & %d & %d & %d \\\\" % (b["name"].replace("_", "\\_"), loc, desc[b["name"]][0], b["K"], b["D"], mut))
open(os.path.join(rd, "table2_rows.tex"), "w").write("\n".join(t2) + "\n")
ab = os.path.join(rd, "ablation_trim.json")
if os.path.exists(ab):
    A = {x["name"]: x for x in json.load(open(ab))}
    lim = max(x["hint_steps"] for x in r)
    t3 = []
    over = 0; red = []
    order = {"m": 0, "sv": 1, "ic": 2}; last = None
    uj = os.path.join(rd, "uncertified.json")
    if os.path.exists(uj):
        unc = {e["name"]: [e["psi_clauses"] or 0, e["hint_steps"] or 0, e["reason"]] for e in json.load(open(uj)) if e["name"] not in EXCLUDE}
    else:
        unc = desc.get("_uncertified", {})
    def unc_rows(g):
        return ["%s & %s & %s & -- & -- & -- & -- & -- & -- & -- & \\no & -- & -- & -- \\\\" % (n.replace("_", "\\_"), "{:,}".format(v[0]) if v[0] else "--", "{:,}".format(v[1]) if v[1] else "--")
                for n, v in sorted(unc.items()) if grp(n) == g]
    for x in sorted(r, key=lambda z: (order[grp(z["name"])], z["name"])):
        g = grp(x["name"])
        if g != last:
            if last is not None: t3.extend(unc_rows(last))
            t3.append("\\rowgroup{14}{%s}" % dict(GROUPS)[g]); last = g
        a = A.get(x["name"])
        if a is None:
            a = dict(hints_raw=x["hint_steps"], hints_trim=x["hint_steps"])
        est = coef[0] * a["hints_raw"] * x["Q"] + coef[1] * a["hints_raw"] + coef[2] * x["psi_clauses"] + coef[3]   # lower bound: untrimmed lemmas are at least as wide
        fits = a["hints_raw"] <= lim; over += (not fits); red.append(a["hints_raw"] / a["hints_trim"])
        t3.append("%s & %s & %s & %dk & %.2f & %.1f & %.1f & %.1f & %.1f & %.2f & \\yes & %s & %dk & %s \\\\" % (
            x["name"].replace("_", "\\_"), "{:,}".format(x["psi_clauses"]), "{:,}".format(x["hint_steps"]), round(x["r1cs"] / 1000),
            x["t_rep"], x["t_wtns"], x["t_prove"], x["t_setup"], x["t_crscheck"] or 0, x["t_verify_ms"],
            "{:,}".format(a["hints_raw"]), round(est / 1000), "\\yes" if fits else "\\no"))
    if last is not None: t3.extend(unc_rows(last))
    open(os.path.join(rd, "table3_rows.tex"), "w").write("\n".join(t3) + "\n")
    put("ablOver", over); put("ablLimit", "{:,}".format(lim).replace(",", "{,}"))
    put("ablRedMin", min(red), "%.1f"); put("ablRedMax", max(red), "%.0f"); put("ablRedMed", st.median(red), "%.1f")
    put("ablRawMin", "{:,}".format(min(A[x["name"]]["hints_raw"] for x in r)).replace(",", "{,}"))
    put("ablRawMax", "{:,}".format(max(A[x["name"]]["hints_raw"] for x in r)).replace(",", "{,}"))
with open(os.path.join(rd, "numbers.tex"), "w") as f:
    f.write("%% generated by make_numbers.py -- do not edit\n")
    for k, v in sorted(N.items()):
        f.write("\\newcommand{\\N%s}{%s\\xspace}\n" % (mname(k), v))
if os.path.exists(ds):
    rows = []
    for b, pts in json.load(open(ds)).items():
        for p in pts:
            rows.append("%s & %d & %s & %s \\\\" % (b.replace("_", "\\_"), p["D"], "{:,}".format(p["psi_clauses"]), "{:,}".format(p["hint_steps"])))
    open(os.path.join(rd, "dscaling_rows.tex"), "w").write("\n".join(rows) + "\n")
print(len(N), "numbers;", "dscaling rows" if os.path.exists(ds) else "no dscaling")
