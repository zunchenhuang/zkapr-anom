// IntroClass smallest, student 769cd81131, buggy revision 010, fixed revision 011.
// Holes L1, L2: left operands of `b >= c` and `c >= d` (buggy b, c; fixed x, x).
// Property: exactly one output, equal to the reference smallest.
// Inputs range over {0..3}: the program only compares and copies its inputs, so its output depends only
// on their relative order, and every order pattern of 4 values (ties included) occurs in this range.
// K: 2
// NIN: 4
// D: 1
// ORIG: 1 2
// REF: 4 4
// BIN: introclass
#include "_common.h"
static int ref_smallest(int num1, int num2, int num3, int num4) {
  int bigger, bigger2, biggest;
  if (num1 < num2) bigger = num1; else bigger = num2;
  if (num4 < num3) bigger2 = num4; else bigger2 = num3;
  if (bigger < bigger2) biggest = bigger; else biggest = bigger2;
  return biggest;
}
static int prog(const unsigned *H, const unsigned *IN) {
  unsigned V[4];
  V[0] = IN[0] & 3u; __CPROVER_assume(V[0] < 4u);
  V[1] = IN[1] & 3u; __CPROVER_assume(V[1] < 4u);
  V[2] = IN[2] & 3u; __CPROVER_assume(V[2] < 4u);
  V[3] = IN[3] & 3u; __CPROVER_assume(V[3] < 4u);
  int a = (int)V[0], b = (int)V[1], c = (int)V[2], d = (int)V[3], x;
  if (a >= b) x = b; else x = a;
  if (SEL5(H[0], a, b, c, d, x) >= c) x = c;
  if (SEL5(H[1], a, b, c, d, x) >= d) x = d;
  return x == ref_smallest(a, b, c, d);
}
