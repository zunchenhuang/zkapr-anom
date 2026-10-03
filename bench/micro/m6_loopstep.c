// K: 1
// NIN: 1
// D: 6
// ORIG: 3
// REF: 2
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  unsigned n = IN[0];
  __CPROVER_assume(n <= 4);
  unsigned s = 0;
  for (unsigned i = 0; i < n; i++) s = s + H[0];
  return s == 2 * n;
}
