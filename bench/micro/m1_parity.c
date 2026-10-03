// K: 2
// NIN: 1
// D: 2
// ORIG: 1 3
// REF: 2 0
// BIN: nonlinear
static int prog(const unsigned *H, const unsigned *IN) {
  unsigned x = IN[0];
  __CPROVER_assume(x <= 7);
  unsigned y = H[0] * x + H[1];
  return y % 2 == 0;
}
