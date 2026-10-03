// K: 2
// NIN: 1
// D: 2
// ORIG: 5 60
// REF: 10 50
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  unsigned x = IN[0];
  __CPROVER_assume(x <= 100);
  unsigned y = x + H[0];
  if (y > H[1]) y = H[1];
  return y >= 10 && y <= 50;
}
