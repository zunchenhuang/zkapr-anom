// Adapted from SV-COMP ReachSafety c/loop-lit/afnp2014.c.
// Hole L1: initial value of x (original 1; injected mutation 0). Loop nondet -> IN[k].
// K: 1
// NIN: 6
// D: 7
// ORIG: 0
// REF: 1
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  int x = (int)H[0];
  int y = 0;
  int k = 0;
  while (y < 1000 && k < 6 && IN[k] != 0) {
    x = x + y;
    y = y + 1;
    k = k + 1;
  }
  return x >= y;
}
