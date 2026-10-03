// Adapted from SV-COMP ReachSafety c/loop-lit/cggmp2005.c.
// Holes L1: initial j (original 10; mutated 11), L2: i increment (original 2; unmutated).
// K: 2
// NIN: 1
// D: 6
// ORIG: 11 2
// REF: 10 2
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  int i = 1, j = (int)H[0];
  while (j >= i) { i = i + (int)H[1]; j = -1 + j; }
  return j == 6;
}
