// IntroClass median, student 9083480332, buggy revision 006, fixed revision 018.
// Holes L1, L2: operators of `c <= a` and `a <= b` in the first condition (buggy <=, <=; fixed >=, >=).
// Property: exactly one output, equal to the reference median.
// Inputs range over {0..2}: the program only compares and copies its inputs, so its output depends only
// on their relative order, and every order pattern of 3 values (ties included) occurs in this range.
// K: 2
// NIN: 3
// D: 1
// ORIG: 1 1
// REF: 3 3
// BIN: introclass
#include "_common.h"
static int ref_median(int num1, int num2, int num3) {
  int bigger12, smaller12, median;
  if (num1 < num2) { bigger12 = num2; smaller12 = num1; } else { bigger12 = num1; smaller12 = num2; }
  if (bigger12 < num3) median = bigger12; else if (num3 > smaller12) median = num3; else median = smaller12;
  return median;
}
static int prog(const unsigned *H, const unsigned *IN) {
  unsigned V[3];
  V[0] = IN[0] & 3u; __CPROVER_assume(V[0] < 3u);
  V[1] = IN[1] & 3u; __CPROVER_assume(V[1] < 3u);
  V[2] = IN[2] & 3u; __CPROVER_assume(V[2] < 3u);
  int a = (int)V[0], b = (int)V[1], c = (int)V[2], out = 0, cnt = 0;
  if ((b >= a && a >= c) || (CMP(H[0], c, a) && CMP(H[1], a, b))) { out = a; cnt++; }
  else if ((a >= b && b >= c) || (a <= b && b <= c)) { out = b; cnt++; }
  else if ((a >= c && c >= b) || (a <= c && c <= b)) { out = c; cnt++; }
  else return 0;   /* the student's program returns 1 without printing */
  return cnt == 1 && out == ref_median(a, b, c);
}
