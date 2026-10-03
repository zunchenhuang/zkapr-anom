"""ZKA-PR prototype: benchmark format, harnesses, and the encoder F.

Benchmark file header (C comments):
  // K: <holes>   // NIN: <nondet inputs>   // D: <unwind bound>
  // ORIG: <buggy hole values>   // REF: <known-correct hole values>
  // BIN: micro|linear|nonlinear
The file defines: static int prog(const unsigned *H, const unsigned *IN)
returning nonzero iff the specification holds on this execution.
"""
import os, re, subprocess, time, json

from config import CBMC, CADICAL, LRATTRIM
QMAX = 4  # clause width after deterministic splitting (part of F)


def load_bench(path):
    src = open(path).read()
    # inline local includes (e.g. the shared helpers of the IntroClass benchmarks)
    src = re.sub(r'#include\s+"([^"]+)"', lambda m: open(os.path.join(os.path.dirname(path), m.group(1))).read(), src)
    hdr = {}
    for key in ("K", "NIN", "D", "ORIG", "REF", "BIN"):
        m = re.search(r"//\s*%s:\s*(.*)" % key, src)
        hdr[key] = m.group(1).strip() if m else None
    b = dict(name=os.path.basename(path)[:-2], path=path, src=src,
             K=int(hdr["K"]), NIN=int(hdr["NIN"]), D=int(hdr["D"]),
             ORIG=[int(x, 0) & 0xffffffff for x in hdr["ORIG"].split()],
             REF=[int(x, 0) & 0xffffffff for x in hdr["REF"].split()] if hdr["REF"] else None,
             BIN=hdr["BIN"])
    return b


def _main(b, holes_expr, inputs_expr, tail):
    lines = [b["src"], "unsigned nondet_uint(void);", "int main(void) {",
             "  unsigned H[%d]; unsigned IN[%d];" % (b["K"], b["NIN"])]
    for i in range(b["K"]):
        lines.append("  H[%d] = %s;" % (i, holes_expr(i)))
    for i in range(b["NIN"]):
        lines.append("  IN[%d] = %s;" % (i, inputs_expr(i)))
    lines += tail + ["  return 0;", "}"]
    return "\n".join(lines) + "\n"


def harness(b, kind, sigma=None, cexs=None):
    nd = lambda i: "nondet_uint()"
    if kind == "unsat":   # Psi /\ not Phi : SAT iff a violation exists
        return _main(b, nd, nd, ["  int ok = prog(H, IN);", '  __CPROVER_assert(ok, "phi");'])
    if kind == "sat":     # Psi : SAT iff some execution completes within D
        return _main(b, nd, nd, ["  prog(H, IN);", '  __CPROVER_assert(0, "reach");'])
    if kind == "direct":  # P_b[L -> sigma], for the bridge check
        return _main(b, lambda i: "%uu" % sigma[i], nd,
                     ["  int ok = prog(H, IN);", '  __CPROVER_assert(ok, "phi");'])
    if kind == "direct_sat":
        return _main(b, lambda i: "%uu" % sigma[i], nd,
                     ["  prog(H, IN);", '  __CPROVER_assert(0, "reach");'])
    if kind == "synth":   # exists H s.t. prog(H, x_i) ok for all counterexamples x_i
        tail = []
        for j, x in enumerate(cexs):
            tail.append("  unsigned IN%d[%d] = {%s};" % (j, b["NIN"], ", ".join("%uu" % v for v in x)))
            tail.append("  int ok%d = prog(H, IN%d);" % (j, j))
        conj = " && ".join("ok%d" % j for j in range(len(cexs)))
        tail.append('  __CPROVER_assert(!(%s), "synth");' % conj)
        return _main(b, nd, nd, tail)
    raise ValueError(kind)


def parse_dimacs(text):
    nv = nc = 0
    clauses, sym = [], {}
    for line in text.splitlines():
        if not line:
            continue
        if line.startswith("p cnf"):
            _, _, nv, nc = line.split(); nv = int(nv)
        elif line.startswith("c "):
            parts = line.split()
            m = re.match(r"main::1::(H|IN)!0@1#(\d+)\[\[(\d+)\]\]$", parts[1])
            if m:
                arr, ver, idx = m.group(1), int(m.group(2)), int(m.group(3))
                lits = []
                for t in parts[2:]:
                    lits.append(t if t in ("TRUE", "FALSE") else int(t))
                key = (arr, idx)
                if key not in sym or ver > sym[key][0]:
                    sym[key] = (ver, lits)
        else:
            c = [int(x) for x in line.split()]
            assert c[-1] == 0
            clauses.append(c[:-1])
    return nv, clauses, sym


def split_clauses(nv, clauses, q=QMAX):
    """Deterministic Tseitin splitting of clauses wider than q (equisatisfiable)."""
    out = []
    for c in clauses:
        if len(c) <= q:
            out.append(list(c)); continue
        rest = list(c)
        first = True
        while len(rest) > (q - 1 if not first else q):
            take = q - 1 if first else q - 2
            nv += 1; y = nv
            head = rest[:take]; rest = rest[take:]
            out.append(head + [y] if first else [-prev] + head + [y])
            prev = y; first = False
        out.append([-prev] + rest)
    for c in out:
        assert 1 <= len(c) <= q
    return nv, out


def encode(b, kind, workdir, **kw):
    """Encoder F: C harness -> (nv, clauses of width <= QMAX, hole bit literals, input bit literals)."""
    os.makedirs(workdir, exist_ok=True)
    cfile = os.path.join(workdir, "h_%s.c" % kind)
    cnf = os.path.join(workdir, "h_%s.cnf" % kind)
    open(cfile, "w").write(harness(b, kind, **kw))
    t0 = time.time()
    r = subprocess.run([CBMC, cfile, "--dimacs", "--outfile", cnf, "--unwind", str(b["D"]),
                        "--no-unwinding-assertions"], capture_output=True, text=True)
    if not os.path.exists(cnf):
        raise RuntimeError("cbmc failed: " + r.stdout[-500:] + r.stderr[-500:])
    nv, clauses, sym = parse_dimacs(open(cnf).read())
    nv, clauses = split_clauses(nv, clauses)
    holes = [sym[("H", i)][1] for i in range(b["K"])] if kind in ("unsat", "sat", "synth") else None
    ins = [sym.get(("IN", i), (0, []))[1] for i in range(b["NIN"])]
    return dict(nv=nv, clauses=clauses, holes=holes, ins=ins, t=time.time() - t0)


def write_cnf(path, nv, clauses, units=()):
    with open(path, "w") as f:
        f.write("p cnf %d %d\n" % (nv, len(clauses) + len(units)))
        for c in clauses:
            f.write(" ".join(map(str, c)) + " 0\n")
        for u in units:
            f.write("%d 0\n" % u)


def hole_units(holes, sigma, w=32):
    units = []
    for i, lits in enumerate(holes):
        assert len(lits) == w, "hole %d has %d bits" % (i, len(lits))
        for bit, l in enumerate(lits):
            assert l not in ("TRUE", "FALSE"), "constant hole bit"
            units.append(l if (sigma[i] >> bit) & 1 else -l)
    return units


def solve(path, lrat=None):
    args = [CADICAL, "-q", path]
    if lrat:
        args = [CADICAL, "-q", "--lrat", "--no-binary", path, lrat]
    r = subprocess.run(args, capture_output=True, text=True)
    model = {}
    if r.returncode == 10:
        for line in r.stdout.splitlines():
            if line.startswith("v "):
                for t in line.split()[1:]:
                    v = int(t)
                    if v:
                        model[abs(v)] = v > 0
    return r.returncode, model


def bits_value(lits, model):
    v = 0
    for bit, l in enumerate(lits):
        if l == "TRUE":
            val = True
        elif l == "FALSE":
            val = False
        else:
            val = model.get(abs(l), False) == (l > 0)
        v |= int(val) << bit
    return v
