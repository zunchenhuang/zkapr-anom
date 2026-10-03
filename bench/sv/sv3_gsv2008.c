// Adapted from SV-COMP ReachSafety c/loop-lit/gsv2008.c.
// Hole L1: initial x (original -50; mutated 0).
// K: 1
// NIN: 1
// D: 3
// ORIG: 0
// REF: 0xffffffce
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  int x = (int)H[0];
  int y = (int)IN[0];
  if (!(-1000 < y && y < 1000000)) return 1;
  while (x < 0) { x = x + y; y++; }
  return y > 0;
}
