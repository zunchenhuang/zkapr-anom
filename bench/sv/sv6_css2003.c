// Adapted from SV-COMP ReachSafety c/loop-lit/css2003.c.
// Holes L1: initial i (original 1; mutated 2), L2: k decrement (original 1; unmutated).
// K: 2
// NIN: 1
// D: 4
// ORIG: 2 1
// REF: 1 1
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  int i = (int)H[0], j = 1, k = (int)IN[0];
  if (!(0 <= k && k <= 1)) return 1;
  while (i < 1000000) {
    i = i + 1; j = j + k; k = k - (int)H[1];
    if (!(1 <= i + k && i + k <= 2 && i >= 1)) return 0;
  }
  return 1;
}
