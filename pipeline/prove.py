"""Setup (customer), prove (vendor), verify (customer), and tampering tests.
Usage: python3 prove.py <workdir>"""
import sys, os, json, time, subprocess, resource, copy

from config import NODE_MODULES, ZKP as ZKP_BIN
NODE_ENV = dict(os.environ, NODE_PATH=NODE_MODULES)


def run(cmd, cwd):
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=NODE_ENV)
    return r, time.time() - t0


def peak_child_mb():
    return resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0


def poseidon(vals, cwd):
    js = ("const {buildPoseidon}=require('circomlibjs');(async()=>{const p=await buildPoseidon();"
          "const h=p(%s.map(BigInt));console.log(p.F.toString(h));process.exit(0)})();" % json.dumps([str(v) for v in vals]))
    r = subprocess.run(["node", "-e", js], cwd=cwd, capture_output=True, text=True, env=NODE_ENV)
    return r.stdout.strip()


def witness(work, inp, name):
    p = os.path.join(work, name + ".json")
    json.dump(inp, open(p, "w"))
    r, t = run(["node", "main_js/generate_witness.js", "main_js/main.wasm", name + ".json", name + ".wtns"], work)
    return r.returncode == 0, t, (r.stdout + r.stderr)[-300:]


if __name__ == "__main__":
    work = sys.argv[1]
    prep = json.load(open(os.path.join(work, "prep.json")))
    raw = json.load(open(os.path.join(work, "witness_raw.json")))
    inp = raw["inp"]
    res = dict(name=prep["name"])
    import time as _t
    inp["c"] = poseidon(inp["sigma"] + [inp["r"]], work)
    ZKP = ZKP_BIN
    # ---- customer: circuit-specific Groth16 setup with a verifiable CRS
    r, t_s = run([ZKP, "setup2", "main.r1cs", "pk.bin", "vk.bin", "aux.bin"], work)
    if r.returncode != 0:
        res["error"] = "setup: " + (r.stdout + r.stderr)[-500:]; json.dump(res, open(os.path.join(work, "prove.json"), "w")); sys.exit(1)
    res.update(json.loads(r.stdout.strip().splitlines()[-1])); res["t_setup_wall"] = t_s
    res["mem_setup_mb"] = peak_child_mb()
    # ---- vendor: check the CRS before proving (subversion zero knowledge)
    r, _ = run([ZKP, "crscheck", "main.r1cs", "pk.bin", "aux.bin"], work)
    c = json.loads(r.stdout.strip().splitlines()[-1])
    res["crs_ok"], res["t_crscheck"] = c["crs_ok"], c["t_crscheck"]
    if not c["crs_ok"]:
        res["error"] = "honest CRS rejected: " + c.get("reason", ""); json.dump(res, open(os.path.join(work, "prove.json"), "w")); sys.exit(1)
    # ---- vendor: witness + proof
    ok, t_w, msg = witness(work, inp, "input")
    res["witness_ok"], res["t_wtns"] = ok, t_w
    if not ok:
        res["error"] = "witness: " + msg; json.dump(res, open(os.path.join(work, "prove.json"), "w"), indent=1); sys.exit(1)
    r, t_p = run([ZKP, "prove2", "main.r1cs", "input.wtns", "pk.bin", "proof.bin", "public.bin"], work)
    if r.returncode != 0:
        res["error"] = "prove: " + (r.stdout + r.stderr)[-500:]; json.dump(res, open(os.path.join(work, "prove.json"), "w")); sys.exit(1)
    res.update(json.loads(r.stdout.strip().splitlines()[-1])); res["t_prove_wall"] = t_p
    res["mem_prove_mb"] = peak_child_mb()
    # ---- customer: verification
    r, _ = run([ZKP, "verify", "vk.bin", "proof.bin", "public.bin"], work)
    v = json.loads(r.stdout.strip().splitlines()[-1])
    res["verify_ok"], res["t_verify_ms"], res["t_verify_first_ms"] = v["ok"], v["t_verify_ms"], v["t_verify_first_ms"]
    # ---- RQ1 tampering
    tam = {}
    orig = [str(x) for x in prep["orig"]]
    # T1: buggy substitution with the fix's refutation and model (recommitted, so only Csat can object)
    t1 = copy.deepcopy(inp); t1["sigma"] = orig; t1["c"] = poseidon(orig + [inp["r"]], work)
    tam["T1_unsafe_sigma"] = not witness(work, t1, "t1")[0]
    # T3: forged refutation: flip one literal of the last non-empty real lemma, or drop the conflict step
    t3 = copy.deepcopy(inp)
    NL = prep["meta"]["NL"]; forged = False
    for a in range(NL - 2, -1, -1):
        for q, x in enumerate(t3["Lits"][a]):
            if x != "0":
                v2 = int(x); P = 21888242871839275222246405745257275088548364400416034343698204186575808495617
                v2 = v2 - P if v2 > P // 2 else v2
                t3["Lits"][a][q] = str((-v2) % P); forged = True; break
        if forged:
            break
    tam["T3_forged_refutation"] = not witness(work, t3, "t3")[0]
    # T3b: wrong multiplicity (claims a lookup that is not in the table)
    t3b = copy.deepcopy(inp); j = next(i for i, m in enumerate(t3b["m1"]) if m != "0")
    t3b["m1"][j] = str(int(t3b["m1"][j]) + 1)
    tam["T3b_forged_lookup"] = not witness(work, t3b, "t3b")[0]
    # T6: model that does not satisfy Psi[sigma]
    t6 = copy.deepcopy(inp); k = next(i for i, m in enumerate(t6["M"]) if m == "1")
    t6["M"][k] = "0"; t6b = copy.deepcopy(inp); t6b["M"] = ["0"] * len(t6b["M"])
    tam["T6_bad_model"] = (not witness(work, t6, "t6")[0]) and (not witness(work, t6b, "t6b")[0])
    # T2: proof checked against a different public commitment (statement for the buggy sigma)
    ZKP = ZKP_BIN
    cb = int(poseidon(orig + [inp["r"]], work))
    open(os.path.join(work, "pub_bad.bin"), "wb").write(cb.to_bytes(32, "little"))
    r, _ = run([ZKP, "verify", "vk.bin", "proof.bin", "pub_bad.bin"], work)
    tam["T2_wrong_statement"] = json.loads(r.stdout.strip().splitlines()[-1])["ok"] is False
    # T4: wrong opening of c
    tam["T4_wrong_opening"] = poseidon(orig + [inp["r"]], work) != inp["c"]
    # T5: corrupted proof (flip one bit in each of 3 positions; each must be rejected)
    pb = bytearray(open(os.path.join(work, "proof.bin"), "rb").read()); rej = True
    for pos in (0, len(pb) // 2, len(pb) - 2):
        bad = bytearray(pb); bad[pos] ^= 1
        open(os.path.join(work, "proof_bad.bin"), "wb").write(bad)
        r, _ = run([ZKP, "verify", "vk.bin", "proof_bad.bin", "public.bin"], work)
        rej = rej and json.loads(r.stdout.strip().splitlines()[-1])["ok"] is False
    tam["T5_corrupted_proof"] = rej
    # T7: subverted CRS (customer side); the vendor's check must reject every variant
    rej, reasons = True, {}
    for mode in ("h", "l", "alpha", "gamma0", "a"):
        run([ZKP, "subvert", mode, "pk.bin", "aux.bin", "pk_sub.bin", "aux_sub.bin"], work)
        r, _ = run([ZKP, "crscheck", "main.r1cs", "pk_sub.bin", "aux_sub.bin"], work)
        o = json.loads(r.stdout.strip().splitlines()[-1]); reasons[mode] = o.get("reason")
        rej = rej and o["crs_ok"] is False
    for f in ("pk_sub.bin", "aux_sub.bin"):
        try:
            os.remove(os.path.join(work, f))
        except FileNotFoundError:
            pass
    tam["T7_subverted_crs"] = rej; res["t7_reasons"] = reasons
    res["tamper_rejected"] = tam
    for f in ("t1", "t3", "t3b", "t6", "t6b"):
        for ext in (".json", ".wtns"):
            try:
                os.remove(os.path.join(work, f + ext))
            except FileNotFoundError:
                pass
    json.dump(res, open(os.path.join(work, "prove.json"), "w"), indent=1)
    print(json.dumps(res))
