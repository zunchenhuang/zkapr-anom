// Adapted from SV-COMP ReachSafety c/loop-invgen/up.c.
// Hole L1: initial k (original 0; mutated -1).
// K: 1
// NIN: 1
// D: 3
// ORIG: 0xffffffff
// REF: 0
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  int n = (int)IN[0];
  int i = 0, k = (int)H[0];
  while (i < n) { i++; k++; }
  int j = 0;
  while (j < n) { if (!(k > 0)) return 0; j++; k--; }
  return 1;
}
