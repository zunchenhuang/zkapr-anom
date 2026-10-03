"""Emit the instance-specific checker circuit (Circom 2).

Public input: c = Poseidon(sigma, r).
Checks: (1) commitment; (2) model M |= Psi_sat[sigma]; (3) trimmed LRAT refutation of
Psi_unsat[sigma] (RUP per lemma), with clause lookups via LogUp whose challenges are
derived in-circuit (Fiat-Shamir) from range-checked, bit-packed witness data.
"""


def bl(x):
    return max(1, int(x).bit_length())


def gen(meta, consts, path):
    K, W, Q, NL, TT, TD = meta["K"], meta["W"], meta["Q"], meta["NL"], meta["TT"], meta["TD"]
    nA, nvA, nB, nU, BASE = meta["nA"], meta["nvA"], meta["nB"], meta["nU"], meta["base"]
    A, B, HA, HB = consts["A"], consts["B"], consts["holesA"], consts["holesB"]
    LB = bl(meta["nvB"]); OFF = 1 << LB; EB = LB + 1
    IDB = bl(BASE + NL); SB = bl(TT); MB1 = bl(TT); MB23 = bl(TT * Q)
    o = []
    w = o.append
    w('pragma circom 2.1.6;')
    w('include "poseidon.circom";\ninclude "bitify.circom";\ninclude "comparators.circom";')
    w('template Main() {')
    w('  signal input c;\n  signal input sigma[%d];\n  signal input r;\n  signal input M[%d];' % (K, nvA))
    w('  signal input Lits[%d][%d];\n  signal input rr[%d];\n  signal input hl[%d][%d];' % (NL, Q, TT, TT, Q))
    w('  signal input fl[%d];\n  signal input uh[%d][%d];\n  signal input bm[%d][%d];\n  signal input tt[%d][%d];' % (TT, TT, Q, TT, Q, TT, Q))
    w('  signal input Did[%d];\n  signal input Dl[%d][4];\n  signal input bD[%d];' % (TD, TD, nB))
    w('  signal input m1[%d];\n  signal input m23[%d];' % (TD + nU + NL, NL * Q + TT))
    # ---- commitment and sigma bits
    w('  component cmh = Poseidon(%d);' % (K + 1))
    w('  for (var i = 0; i < %d; i++) { cmh.inputs[i] <== sigma[i]; }' % K)
    w('  cmh.inputs[%d] <== r;\n  cmh.out === c;' % K)
    w('  component sb[%d];' % K)
    w('  for (var i = 0; i < %d; i++) { sb[i] = Num2Bits(%d); sb[i].in <== sigma[i]; }' % (K, W))
    # ---- model check (straight-line)
    w('  for (var v = 0; v < %d; v++) { M[v] * (M[v] - 1) === 0; }' % nvA)

    def lv(l):  # literal value as linear expression over M
        return ('M[%d]' % (l - 1)) if l > 0 else ('(1 - M[%d])' % (-l - 1))

    def nlv(l):  # 1 - value
        return ('(1 - M[%d])' % (l - 1)) if l > 0 else ('M[%d]' % (-l - 1))
    w('  signal cp[%d][2];' % nA)
    for i in range(K):
        for j in range(W):
            w('  %s === sb[%d].out[%d];' % (lv(HA[i][j]), i, j))
    for i, cl in enumerate(A):
        n = [nlv(l) for l in cl]
        if len(cl) == 1:
            w('  %s === 0;' % n[0])
        elif len(cl) == 2:
            w('  %s * %s === 0;' % (n[0], n[1]))
        elif len(cl) == 3:
            w('  cp[%d][0] <== %s * %s; cp[%d][0] * %s === 0;' % (i, n[0], n[1], i, n[2]))
        else:
            w('  cp[%d][0] <== %s * %s; cp[%d][1] <== cp[%d][0] * %s; cp[%d][1] * %s === 0;'
              % (i, n[0], n[1], i, i, n[2], i, n[3]))
        if len(cl) <= 2:
            w('  cp[%d][0] <== 0;' % i)
        if len(cl) <= 3:
            w('  cp[%d][1] <== 0;' % i)
    # ---- range checks and booleans (all feed Fiat-Shamir)
    w('  component lb[%d][%d]; component rb[%d]; component hb[%d][%d]; component tb[%d][%d];' % (NL, Q, TT, TT, Q, TT, Q))
    w('  component db[%d]; component dlb[%d][4]; component mb1[%d]; component mb23[%d];' % (TD, TD, TD + nU + NL, NL * Q + TT))
    w('  for (var a = 0; a < %d; a++) { for (var q = 0; q < %d; q++) { lb[a][q] = Num2Bits(%d); lb[a][q].in <== Lits[a][q] + %d; } }' % (NL, Q, EB, OFF))
    w('  for (var s = 0; s < %d; s++) {' % TT)
    w('    rb[s] = Num2Bits(%d); rb[s].in <== rr[s];' % IDB)
    w('    fl[s] * (fl[s] - 1) === 0;')
    w('    for (var q = 0; q < %d; q++) {' % Q)
    w('      hb[s][q] = Num2Bits(%d); hb[s][q].in <== hl[s][q] + %d;' % (EB, OFF))
    w('      tb[s][q] = Num2Bits(%d); tb[s][q].in <== tt[s][q];' % SB)
    w('      uh[s][q] * (uh[s][q] - 1) === 0; bm[s][q] * (bm[s][q] - 1) === 0;')
    w('    }\n  }')
    w('  for (var j = 0; j < %d; j++) { db[j] = Num2Bits(%d); db[j].in <== Did[j];' % (TD, IDB))
    w('    for (var q = 0; q < 4; q++) { dlb[j][q] = Num2Bits(%d); dlb[j][q].in <== Dl[j][q] + %d; } }' % (EB, OFF))
    w('  for (var j = 0; j < %d; j++) { bD[j] * (bD[j] - 1) === 0; }' % nB)
    w('  for (var j = 0; j < %d; j++) { mb1[j] = Num2Bits(%d); mb1[j].in <== m1[j]; }' % (TD + nU + NL, MB1))
    w('  for (var j = 0; j < %d; j++) { mb23[j] = Num2Bits(%d); mb23[j].in <== m23[j]; }' % (NL * Q + TT, MB23))
    # ---- pack bits into field elements (linear), then hash chain
    nbits = NL * Q * EB + TT * (IDB + 1 + Q * (EB + SB + 2)) + TD * (IDB + 4 * EB) + nB \
        + (TD + nU + NL) * MB1 + (NL * Q + TT) * MB23
    NC = (nbits + 249) // 250
    NH = (NC + 14) // 15
    w('  signal chunk[%d];' % (NH * 15))
    w('  var acc = 0; var sh = 0; var ci = 0;')

    def push(expr):
        return ('    acc += (%s) * (2 ** sh); sh++; if (sh == 250) { chunk[ci] <== acc; ci++; acc = 0; sh = 0; }' % expr)
    w('  for (var a = 0; a < %d; a++) { for (var q = 0; q < %d; q++) { for (var k = 0; k < %d; k++) {' % (NL, Q, EB))
    w(push('lb[a][q].out[k]') + ' } } }')
    w('  for (var s = 0; s < %d; s++) {' % TT)
    w('    for (var k = 0; k < %d; k++) {' % IDB); w(push('rb[s].out[k]') + ' }')
    w(push('fl[s]'))
    w('    for (var q = 0; q < %d; q++) {' % Q)
    w('      for (var k = 0; k < %d; k++) {' % EB); w(push('hb[s][q].out[k]') + ' }')
    w('      for (var k = 0; k < %d; k++) {' % SB); w(push('tb[s][q].out[k]') + ' }')
    w(push('uh[s][q]')); w(push('bm[s][q]'))
    w('    }\n  }')
    w('  for (var j = 0; j < %d; j++) { for (var k = 0; k < %d; k++) {' % (TD, IDB)); w(push('db[j].out[k]') + ' }')
    w('    for (var q = 0; q < 4; q++) { for (var k = 0; k < %d; k++) {' % EB); w(push('dlb[j][q].out[k]') + ' } } }')
    w('  for (var j = 0; j < %d; j++) {' % nB); w(push('bD[j]') + ' }')
    w('  for (var j = 0; j < %d; j++) { for (var k = 0; k < %d; k++) {' % (TD + nU + NL, MB1)); w(push('mb1[j].out[k]') + ' } }')
    w('  for (var j = 0; j < %d; j++) { for (var k = 0; k < %d; k++) {' % (NL * Q + TT, MB23)); w(push('mb23[j].out[k]') + ' } }')
    w('  if (sh > 0) { chunk[ci] <== acc; ci++; }')
    w('  for (var j = ci; j < %d; j++) { chunk[j] <== 0; }' % (NH * 15))
    w('  component hs[%d];' % NH)
    w('  for (var h = 0; h < %d; h++) { hs[h] = Poseidon(16);' % NH)
    w('    if (h == 0) { hs[h].inputs[0] <== c; } else { hs[h].inputs[0] <== hs[h-1].out; }')
    w('    for (var j = 0; j < 15; j++) { hs[h].inputs[j+1] <== chunk[h*15 + j]; } }')
    w('  component chb = Poseidon(2); chb.inputs[0] <== hs[%d].out; chb.inputs[1] <== 1;' % (NH - 1))
    w('  component chg = Poseidon(2); chg.inputs[0] <== hs[%d].out; chg.inputs[1] <== 2;' % (NH - 1))
    w('  signal g; g <== chg.out;')
    w('  signal bp[%d]; bp[1] <== chb.out; bp[0] <== 1;' % (Q + 1))
    w('  for (var j = 2; j <= %d; j++) { bp[j] <== bp[j-1] * bp[1]; }' % Q)
    # ---- steps: owners, T1 reads, units, T23 reads, T3 entries
    w('  signal ow[%d]; fl[0] === 1; ow[0] <== 0;' % TT)
    w('  for (var s = 1; s < %d; s++) { ow[s] <== ow[s-1] + fl[s]; }' % TT)
    w('  ow[%d] === %d;' % (TT - 1, NL - 1))
    w('  signal pr1[%d][%d]; signal inv1[%d]; signal ux[%d][%d]; signal bo[%d]; signal bx[%d]; signal inv3[%d]; signal tm3[%d];'
      % (TT, Q, TT, TT, Q, TT, TT, TT, TT))
    w('  component iz[%d][%d]; signal nd[%d][%d]; signal blt[%d][%d]; signal spv[%d][%d]; signal b2[%d][%d]; signal b3[%d][%d]; signal inv23[%d][%d]; signal t23[%d][%d];'
      % ((TT, Q) * 8))
    w('  var sumR1 = 0; var sumR23 = 0; var sumT23 = 0;')
    w('  for (var s = 0; s < %d; s++) {' % TT)
    w('    var e = 1; if (s < %d) { e = fl[s+1]; }' % (TT - 1))
    w('    var fp1 = %d + ow[s] - 1 - rr[s];' % BASE)
    w('    var us = 0; var x = 0;')
    w('    for (var q = 0; q < %d; q++) { pr1[s][q] <== bp[q+1] * hl[s][q]; fp1 += pr1[s][q];' % Q)
    w('      ux[s][q] <== uh[s][q] * hl[s][q]; x += ux[s][q]; us += uh[s][q]; }')
    w('    us === 1 - e;')
    w('    inv1[s] <-- 1 / (g - fp1); inv1[s] * (g - fp1) === 1; sumR1 += inv1[s];')
    w('    bo[s] <== bp[1] * ow[s]; bx[s] <== bp[2] * x;')
    w('    var fp3 = 1 + e + bo[s] + bx[s] + bp[3] * s;')
    w('    inv3[s] <-- 1 / (g - fp3); inv3[s] * (g - fp3) === 1;')
    w('    tm3[s] <== m23[%d + s] * inv3[s]; sumT23 += tm3[s];' % (NL * Q))
    w('    for (var q = 0; q < %d; q++) {' % Q)
    w('      iz[s][q] = IsZero(); iz[s][q].in <== hl[s][q];')
    w('      nd[s][q] <== (1 - iz[s][q].out) * (1 - uh[s][q]);')
    w('      blt[s][q] <== bm[s][q] * hl[s][q];')
    w('      spv[s][q] <== bm[s][q] * (s - 1 - tt[s][q]);')
    w('      b2[s][q] <== bp[2] * (hl[s][q] - 2 * blt[s][q]);')
    w('      b3[s][q] <== bp[3] * spv[s][q];')
    w('      var fp23 = bm[s][q] + bo[s] + b2[s][q] + b3[s][q];')
    w('      inv23[s][q] <-- 1 / (g - fp23); inv23[s][q] * (g - fp23) === 1;')
    w('      t23[s][q] <== nd[s][q] * inv23[s][q]; sumR23 += t23[s][q];')
    w('    }\n  }')
    # ---- lemma table (T1 entries and T2 entries)
    w('  signal prL[%d][%d]; signal invL[%d]; signal tL[%d]; signal b2L[%d][%d]; signal invT2[%d][%d]; signal tT2[%d][%d];'
      % (NL, Q, NL, NL, NL, Q, NL, Q, NL, Q))
    w('  var sumT1 = 0;')
    w('  for (var a = 0; a < %d; a++) {' % NL)
    w('    var fpl = %d + a;' % BASE)
    w('    for (var q = 0; q < %d; q++) { prL[a][q] <== bp[q+1] * Lits[a][q]; fpl += prL[a][q];' % Q)
    w('      b2L[a][q] <== bp[2] * Lits[a][q];')
    w('      invT2[a][q] <-- 1 / (g - bp[1] * a - b2L[a][q]); invT2[a][q] * (g - bp[1] * a - b2L[a][q]) === 1;')
    w('      tT2[a][q] <== m23[a * %d + q] * invT2[a][q]; sumT23 += tT2[a][q]; }' % Q)
    w('    invL[a] <-- 1 / (g - fpl); invL[a] * (g - fpl) === 1;')
    w('    tL[a] <== m1[%d + a] * invL[a]; sumT1 += tL[a];' % (TD + nU))
    w('  }')
    w('  for (var q = 0; q < %d; q++) { Lits[%d][q] === 0; }' % (Q, NL - 1))
    # ---- unit entries (hole bits, from sigma)
    w('  var HB[%d][%d] = [%s];' % (K, W, ",".join("[" + ",".join(map(str, row)) + "]" for row in HB)))
    w('  signal bu[%d][%d]; signal invU[%d][%d]; signal tU[%d][%d];' % (K, W, K, W, K, W))
    w('  for (var i = 0; i < %d; i++) { for (var j = 0; j < %d; j++) {' % (K, W))
    w('    bu[i][j] <== bp[1] * sb[i].out[j];')
    w('    var fpu = %d + i * %d + j + HB[i][j] * (2 * bu[i][j] - bp[1]);' % (nB + 1, W))
    w('    invU[i][j] <-- 1 / (g - fpu); invU[i][j] * (g - fpu) === 1;')
    w('    tU[i][j] <== m1[%d + i * %d + j] * invU[i][j]; sumT1 += tU[i][j]; } }' % (TD, W))
    # ---- distinct-original list D
    w('  signal prD[%d][4]; signal invD[%d]; signal tD[%d]; var sumD = 0;' % (TD, TD, TD))
    w('  for (var j = 0; j < %d; j++) { var fpd = Did[j];' % TD)
    w('    for (var q = 0; q < 4; q++) { prD[j][q] <== bp[q+1] * Dl[j][q]; fpd += prD[j][q]; }')
    w('    invD[j] <-- 1 / (g - fpd); invD[j] * (g - fpd) === 1; sumD += invD[j];')
    w('    tD[j] <== m1[j] * invD[j]; sumT1 += tD[j]; }')
    # ---- constant originals table (straight-line)
    w('  signal invO[%d]; signal tO[%d]; var sumO = 0;' % (nB, nB))
    for i, cl in enumerate(B):
        fp = "%d" % (i + 1) + "".join(" + %d * bp[%d]" % (l, k + 1) for k, l in enumerate(cl))
        w('  invO[%d] <-- 1 / (g - (%s)); invO[%d] * (g - (%s)) === 1; tO[%d] <== bD[%d] * invO[%d]; sumO += tO[%d];'
          % (i, fp, i, fp, i, i, i, i))
    # ---- LogUp identities
    w('  sumR1 === sumT1;\n  sumD === sumO;\n  sumR23 === sumT23;')
    w('}')
    w('component main {public [c]} = Main();')
    open(path, "w").write("\n".join(o) + "\n")
    return dict(LB=LB, IDB=IDB, SB=SB, MB1=MB1, MB23=MB23, nbits=nbits, NH=NH)
