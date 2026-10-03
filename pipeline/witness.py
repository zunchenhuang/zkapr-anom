"""Vendor-side witness construction for the ZKA-PR checker circuit."""
import os, json, subprocess, time, secrets
from common import *

P = 21888242871839275222246405745257275088548364400416034343698204186575808495617


def rup(n_real, db, C, hints):
    """Replay reverse unit propagation; return per-hint (unit_slot | None, [(mode, ref)])."""
    Cset, units, steps = set(C), {}, []   # units: literal -> local step index
    for si, h in enumerate(hints):
        lits = db[h]
        fals, free = [], []
        for q, l in enumerate(lits):
            if l in Cset:
                fals.append((q, 0, None))
            elif -l in units:
                fals.append((q, 1, units[-l]))
            else:
                free.append(q)
        if not free:
            steps.append((h, None, fals)); return steps        # conflict
        if len(free) != 1:
            raise RuntimeError("hint %d not unit (%d free)" % (h, len(free)))
        units[lits[free[0]]] = si
        steps.append((h, free[0], fals))
    raise RuntimeError("no conflict reached")


def flatten(lem, db0):
    """Inline unit lemmas into later derivations (pure-propagation chains).
    Every resulting lemma is re-checked by rup(); on failure return None."""
    by_id = {lid: (lits, hints) for (lid, lits, hints) in lem}
    out = []
    for (lid, lits, hints) in lem:
        if len(lits) == 1 and lits:
            continue                      # inlined where used
        seq, done = [], set()

        def expand(h):
            if h in by_id and len(by_id[h][0]) == 1:
                if h in done:
                    return
                for hh in by_id[h][1]:
                    expand(hh)
                done.add(h)
            else:
                seq.append(h)
        for h in hints:
            expand(h)
        out.append((lid, lits, seq))
    # verify with RUP replay (drop duplicate hints that no longer propagate)
    db = dict(db0)
    res = []
    for (lid, lits, seq) in out:
        try:
            steps = rup_lenient(db, lits, seq)
        except RuntimeError:
            return None
        db[lid] = lits
        res.append((lid, lits, steps))
        if not lits:
            return res
    return None


def rup_lenient(db, C, hints):
    """Like rup(), but skips hints that are already satisfied or propagate nothing new."""
    Cset, units, steps = set(C), {}, []
    for h in hints:
        lits = db[h]
        if any((l in units) or (-l in Cset) for l in lits):
            continue                        # satisfied: useless hint
        fals, free = [], []
        for q, l in enumerate(lits):
            if l in Cset:
                fals.append((q, 0, None))
            elif -l in units:
                fals.append((q, 1, units[-l]))
            else:
                free.append(q)
        if not free:
            steps.append((h, None, fals)); return steps
        if len(free) != 1:
            raise RuntimeError("not unit")
        units[lits[free[0]]] = len(steps)
        steps.append((h, free[0], fals))
    raise RuntimeError("no conflict")


def parse_lrat(path):
    out = []
    for line in open(path):
        t = line.split()
        if not t or t[1] == "d":
            continue
        z = t.index("0", 1)
        lits = [int(x) for x in t[1:z]]
        hints = [int(x) for x in t[z + 1:-1]]
        if any(h < 0 for h in hints):
            raise RuntimeError("RAT hint")
        out.append((int(t[0]), lits, hints))
    return out


def rnd(x, g):
    return ((x + g - 1) // g) * g


def build(b, work, sigma, pad=16, W=32, compact=False):
    t0 = time.time()
    U = encode(b, "unsat", work); A = encode(b, "sat", work)
    tenc = U["t"] + A["t"]
    # model for Psi[sigma]
    uA = hole_units(A["holes"], sigma)
    pa = os.path.join(work, "wit_sat.cnf"); write_cnf(pa, A["nv"], A["clauses"], uA)
    rc, model = solve(pa)
    if rc != 10:
        raise RuntimeError("Psi[sigma] unsatisfiable: vacuous repair")
    M = [1 if model.get(v, False) else 0 for v in range(1, A["nv"] + 1)]
    # refutation of Psi[sigma] /\ not Phi
    uB = hole_units(U["holes"], sigma)
    pb = os.path.join(work, "wit_unsat.cnf"); write_cnf(pb, U["nv"], U["clauses"], uB)
    t1 = time.time()
    rc, _ = solve(pb, lrat=os.path.join(work, "proof.lrat"))
    if rc != 20:
        raise RuntimeError("violation remains: not a repair")
    subprocess.run([LRATTRIM, "--ascii", pb, os.path.join(work, "proof.lrat"),
                    os.path.join(work, "proof.trim.lrat")], capture_output=True)
    lem = parse_lrat(os.path.join(work, "proof.trim.lrat"))
    tsolve = time.time() - t1
    nB, nU = len(U["clauses"]), len(uB)
    db = {i + 1: list(c) for i, c in enumerate(U["clauses"])}
    for j, u in enumerate(uB):
        db[nB + 1 + j] = [u]
    # replay each lemma, stop at the empty clause; try unit-lemma inlining first
    real = flatten(lem, db) if compact else None
    compacted = real is not None
    if real is None:
        real = []
        for (lid, lits, hints) in lem:
            steps = rup(None, db, lits, hints)
            db[lid] = lits
            real.append((lid, lits, steps))
            if not lits:
                break
    for (lid, lits, _) in real:
        db[lid] = lits
    assert real and not real[-1][1], "no empty clause"
    nL = len(real)
    Q = max([QMAX] + [len(l) for (_, l, _) in real])
    NL = rnd(nL + 1, pad); npad = NL - nL
    T = sum(len(s) for (_, _, s) in real)
    TT = rnd(T + npad, pad); extra = TT - T - npad
    base = nB + nU + 1
    idmap = {i: i for i in range(1, base)}
    for o, (lid, _, _) in enumerate(real):
        idmap[lid] = base + npad + o
    ref_orig = sorted({h for (_, _, st) in real for (h, _, _) in st if h <= nB})
    p = ref_orig[0] if ref_orig else 1
    # lemma table
    Lits = [db[p] + [0] * (Q - len(db[p])) for _ in range(npad)]
    Lits += [l + [0] * (Q - len(l)) for (_, l, _) in real]
    # steps
    S = []  # (o, d, hl, f, uh, bm, tt)
    for o in range(npad):
        cnt = 1 + (extra if o == 0 else 0)
        for j in range(cnt):
            last = (j == cnt - 1)
            hl = Lits[o][:]
            uh = [0] * Q
            if not last:
                uh[0] = 1
            pos = [("c", q) if (hl[q] != 0 and uh[q] == 0) else None for q in range(Q)]
            S.append([o, p, hl, int(j == 0), uh, [0] * Q, [0] * Q, pos])
    for o2, (lid, lits, steps) in enumerate(real):
        o = npad + o2
        first_s = len(S)
        for j, (h, uslot, fals) in enumerate(steps):
            hl = db[h] + [0] * (Q - len(db[h]))
            uh = [0] * Q
            if uslot is not None:
                uh[uslot] = 1
            bm, tt, pos = [0] * Q, [0] * Q, [None] * Q
            for (q, mode, ref) in fals:
                if mode == 1:
                    bm[q] = 1; sp = first_s + ref; s = len(S); tt[q] = s - sp - 1
                    pos[q] = ("u", sp)
                else:
                    pos[q] = ("c", Lits[o].index(hl[q]))
            S.append([o, idmap[h], hl, int(j == 0), uh, bm, tt, pos])
    assert len(S) == TT
    for s in range(1, TT):
        pass
    # distinct-original list D
    D = list(ref_orig) if ref_orig else [p]
    fill = 1
    while len(D) < rnd(len(D), pad):
        while fill in D:
            fill += 1
        D.append(fill)
    D = sorted(D); TD = len(D)
    Dl = [db[i] + [0] * (4 - len(db[i])) for i in D]
    # multiplicities
    t1_index = {i: j for j, i in enumerate(D)}
    for j in range(nU):
        t1_index[nB + 1 + j] = TD + j
    for o in range(NL):
        t1_index[base + o] = TD + nU + o
    m1 = [0] * (TD + nU + NL)
    for st in S:
        m1[t1_index[st[1]]] += 1
    m23 = [0] * (NL * Q + TT)
    for s, st in enumerate(S):
        o, pos = st[0], st[7]
        for q in range(Q):
            if st[2][q] == 0 or st[4][q] == 1:
                continue
            kind, ref = pos[q]
            m23[o * Q + ref if kind == "c" else NL * Q + ref] += 1
    bD = [0] * nB
    for i in D:
        bD[i - 1] = 1
    r = secrets.randbelow(P)
    f = lambda v: str(v % P)
    inp = dict(sigma=[str(x) for x in sigma], r=str(r), M=[str(x) for x in M],
               Lits=[[f(x) for x in row] for row in Lits],
               rr=[str(base + st[0] - 1 - st[1]) for st in S],
               hl=[[f(x) for x in st[2]] for st in S],
               fl=[str(st[3]) for st in S], uh=[[str(x) for x in st[4]] for st in S],
               bm=[[str(x) for x in st[5]] for st in S], tt=[[str(x) for x in st[6]] for st in S],
               Did=[str(i) for i in D], Dl=[[f(x) for x in row] for row in Dl],
               bD=[str(x) for x in bD], m1=[str(x) for x in m1], m23=[str(x) for x in m23])
    meta = dict(nA=len(A["clauses"]), nvA=A["nv"], nB=nB, nvB=U["nv"], nU=nU, K=b["K"], W=W,
                Q=Q, NL=NL, nL=nL, TT=TT, T=T, TD=TD, base=base, pad=pad,
                t_encode=tenc, t_solve=tsolve, compacted=compacted, lrat_lemmas=len(lem), lrat_hints=sum(len(h) for (_, _, h) in lem), t_wit=time.time() - t0)
    consts = dict(A=A["clauses"], B=U["clauses"], holesA=A["holes"], holesB=U["holes"])
    return inp, meta, consts
