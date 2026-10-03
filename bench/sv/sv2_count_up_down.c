// Adapted from SV-COMP ReachSafety c/loops/count_up_down-1.c.
// Holes L1: initial y (original 0; mutated 1), L2: y increment (original 1; mutated 2).
// K: 2
// NIN: 1
// D: 2
// ORIG: 1 2
// REF: 0 1
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  unsigned n = IN[0];
  unsigned x = n, y = H[0];
  while (x > 0) { x--; y = y + H[1]; }
  return y == n;
}
