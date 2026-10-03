// K: 1
// NIN: 3
// D: 4
// ORIG: 15
// REF: 8
// BIN: linear
static int prog(const unsigned *H, const unsigned *IN) {
  unsigned s = H[0];
  for (int i = 0; i < 3; i++) { __CPROVER_assume(IN[i] <= 10); s = s + IN[i]; }
  return s >= 5 && s <= 40;
}
