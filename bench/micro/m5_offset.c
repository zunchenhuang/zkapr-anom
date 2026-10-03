// K: 2
// NIN: 1
// D: 2
// ORIG: 5 1
// REF: 5 2
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  unsigned x = IN[0];
  __CPROVER_assume(x <= 20);
  unsigned y = x + H[0];
  unsigned z = y - H[1];
  return z == x + 3;
}
