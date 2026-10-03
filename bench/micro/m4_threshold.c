// K: 1
// NIN: 1
// D: 2
// ORIG: 100
// REF: 500
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  unsigned x = IN[0];
  __CPROVER_assume(x < 1000);
  unsigned r = 0;
  if (x > H[0]) r = x - H[0];
  return r < 500;
}
