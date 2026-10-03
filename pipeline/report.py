"""Aggregate per-benchmark JSON into results.csv/json, summary, LaTeX table rows, and the scaling figure.
Usage: python3 report.py [workdir] [outdir]"""
import json, glob, os, csv, subprocess, statistics as st, sys
from config import ZKP, WORK, RESULTS
from common import parse_dimacs, split_clauses

POS = {2: 240, 3: 261, 16: 609}   # measured circomlib Poseidon(n) constraint counts (--O2)


def breakdown(meta, circ, A):
    K, W, Q, NL, TT, TD = meta["K"], meta["W"], meta["Q"], meta["NL"], meta["TT"], meta["TD"]
    nB, nU, nvA = meta["nB"], meta["nU"], meta["nvA"]
    EB, IDB, SB, MB1, MB23 = circ["LB"] + 1, circ["IDB"], circ["SB"], circ["MB1"], circ["MB23"]
    return dict(
        commit=K * W + POS.get(K + 1, 0),
        model=nvA + sum(len(c) - 1 for c in A if len(c) >= 2),
        clause_table=3 * nB,
        range=NL * Q * EB + TT * (IDB + 1 + Q * (EB + SB + 2)) + TD * (IDB + 4 * EB) + (TD + nU + NL) * MB1 + (NL * Q + TT) * MB23,
        fs_hash=circ["NH"] * POS[16] + 2 * POS[2] + (Q - 1),
        refutation=TT * (2 * Q + 4 + 9 * Q + 1) + NL * (4 * Q + 2) + 3 * K * W + 6 * TD)


def main(work, out):
    os.makedirs(out, exist_ok=True)
    rows = []
    for p in sorted(glob.glob(os.path.join(work, "*", "prove.json"))):
        w = os.path.dirname(p)
        pr = json.load(open(p)); pp = json.load(open(os.path.join(w, "prep.json")))
        if not pr.get("verify_ok"):
            continue
        tf = os.path.join(w, "timing.json"); tq = json.load(open(tf)) if os.path.exists(tf) else {}
        quiet = tq.get("prove_status") == 0 and tq.get("ok") is True
        if quiet:
            pr = dict(pr, t_setup=tq["t_setup"], t_prove=tq["t_prove"], t_verify_ms=tq["t_verify_ms"],
                      t_crscheck=tq.get("t_crscheck", pr.get("t_crscheck")),
                      mem_prove_mb=tq["prove_mem_mb"], mem_setup_mb=tq["setup_mem_mb"], pk_bytes=tq["pk_bytes"])
        m = pp["meta"]
        nv, cl, _ = parse_dimacs(open(os.path.join(w, "h_sat.cnf")).read()); _, A = split_clauses(nv, cl)
        bd = breakdown(m, pp["circuit"], A); tot = sum(bd.values())
        rows.append(dict(
            name=pp["name"], set="IC" if pp["name"].startswith("ic_") else ("Micro" if pp["name"].startswith("m") else "SV"), bin=pp["bin"], k=pp["K"], D=pp["D"],
            psi_clauses=m["nB"], psi_vars=m["nvB"], psi_sat_clauses=m["nA"], lemmas=m["nL"], hint_steps=m["T"],
            Q=m["Q"], NL=m["NL"], TT=m["TT"], TD=m["TD"], r1cs=pr["constraints"], wires=pr["wires"], pred=tot,
            **{"c_" + k: v for k, v in bd.items()}, **{"share_" + k: v / tot for k, v in bd.items()},
            t_rep=pp["repair"]["time"], rep_iters=pp["repair"]["iters"], sigma=" ".join(map(str, pp["repair"]["sigma"])),
            orig=" ".join(map(str, pp["orig"])), t_wit=m["t_wit"], t_wtns=pr["t_wtns"], t_prove=pr["t_prove"],
            t_inst=pp["t_inst_encode"], t_compile=pp["t_compile"], t_setup=pr["t_setup"], t_crscheck=pr.get("t_crscheck"), aux_mb=pr.get("aux_bytes", 0) / 2**20, t_verify_ms=pr["t_verify_ms"],
            proof_bytes=pr["proof_bytes"], pk_mb=pr["pk_bytes"] / 2**20, mem_prove_mb=pr["mem_prove_mb"],
            timing="quiet" if quiet else "contended", bridge_ok=pp["bridge_ok"], bridge_ref_ok=pp.get("bridge_ref_ok"),
            orig_violates=pp["orig_violates"], **{"tam_" + k: v for k, v in pr["tamper_rejected"].items()}))
    for i, r in enumerate(rows):   # T2b: proof under another instance's verification key
        j = rows[(i + 1) % len(rows)]
        wa, wb = os.path.join(work, r["name"]), os.path.join(work, j["name"])
        o = subprocess.run([ZKP, "verify", wb + "/vk.bin", wa + "/proof.bin", wa + "/public.bin"], capture_output=True, text=True).stdout
        r["tam_T2b_other_instance_vk"] = json.loads(o.strip().splitlines()[-1])["ok"] is False if len(rows) > 1 else None
    if not rows:
        print("no completed benchmarks"); return
    with open(os.path.join(out, "results.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); [wr.writerow(r) for r in rows]
    json.dump(rows, open(os.path.join(out, "results.json"), "w"), indent=1)
    # benchmarks without a verified proof (not run, repair failed, compile failed, ...)
    from config import ROOT
    done = {x["name"] for x in rows}; unc = []
    for f in sorted(glob.glob(os.path.join(ROOT, "bench", "*", "*.c"))):
        n = os.path.basename(f)[:-2]
        if n in done or n.startswith("_"):
            continue
        pj = os.path.join(work, n, "prep.json"); e = dict(name=n, psi_clauses=None, hint_steps=None, reason="not run")
        if os.path.exists(pj):
            pp = json.load(open(pj)); m = pp.get("meta") or {}
            e.update(psi_clauses=m.get("nB"), hint_steps=m.get("T"))
            if not pp.get("repair", {}).get("ok", True): e["reason"] = "no repair found"
            elif pp.get("compile_ok") is False: e["reason"] = "circuit compilation failed"
            elif pp.get("compile_ok") is None: e["reason"] = pp.get("error", "preparation failed")[:80]
            else: e["reason"] = "proving or verification failed"
        unc.append(e)
    json.dump(unc, open(os.path.join(out, "uncertified.json"), "w"), indent=1)
    M = [x for x in rows if x["set"] == "Micro"]; S = [x for x in rows if x["set"] == "SV"]; I = [x for x in rows if x["set"] == "IC"]
    med = lambda k, g: st.median([x[k] for x in g]) if g else None
    summ = {n: {k: med(k, g) for k in ("t_rep", "t_wtns", "t_prove", "t_setup", "t_crscheck", "t_verify_ms", "r1cs", "hint_steps")} for n, g in (("Micro", M), ("SV", S), ("All", rows))}
    ratio = [(x["t_prove"] + x["t_setup"] + (x["t_crscheck"] or 0)) / x["t_rep"] for x in rows]
    summ["certify_over_repair"] = dict(median=st.median(ratio), min=min(ratio), max=max(ratio))
    summ["tamper_all_rejected"] = all(all(v for k, v in x.items() if k.startswith("tam_") and v is not None) for x in rows)
    json.dump(summ, open(os.path.join(out, "summary.json"), "w"), indent=1)
    lines = []
    for g in (M, S):
        for x in g:
            lines.append(" & ".join([x["name"].replace("_", "\\_"), str(x["k"]), str(x["D"]), "{:,}".format(x["psi_clauses"]),
                                     "{:,}".format(x["hint_steps"]), "%.0fk" % (x["r1cs"] / 1e3), "%.2f" % x["t_rep"], "%.1f" % x["t_wtns"],
                                     "%.1f" % x["t_prove"], "%.1f" % x["t_setup"], "%.1f" % (x["t_crscheck"] or 0), "%.2f" % x["t_verify_ms"], "%.0f" % x["mem_prove_mb"]]) + " \\\\")
        lines.append("\\midrule")
    open(os.path.join(out, "table_rows.tex"), "w").write("\n".join(lines[:-1]) + "\n")
    try:
        from make_figure import plot
        plot(rows, out)
    except ImportError:
        print("matplotlib not installed: figure skipped")
    for r in rows:
        print("%-18s steps=%5d r1cs=%7d (pred %+.1f%%) rep=%.2fs setup=%.1fs prove=%.1fs ver=%.2fms tamper_ok=%s bridge=%s"
              % (r["name"], r["hint_steps"], r["r1cs"], 100.0 * (r["pred"] - r["r1cs"]) / r["r1cs"], r["t_rep"], r["t_setup"],
                 r["t_prove"], r["t_verify_ms"], all(v for k, v in r.items() if k.startswith("tam_") and v is not None), r["bridge_ok"]))
    print(json.dumps(summ["All"]), json.dumps(summ["certify_over_repair"]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else WORK, sys.argv[2] if len(sys.argv) > 2 else RESULTS)
