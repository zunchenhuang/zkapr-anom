// IntroClass median, student 3b2376ab97, buggy revision 000, fixed revision 016.
// Holes L1: operator of `n1 < n2` (buggy <, fixed <=); L2, L3: printed variables in the else branch
// (buggy n3, n1; fixed n1, n3). Property: exactly one output, equal to the reference median.
// Inputs range over {0..2}: the program only compares and copies its inputs, so its output depends only
// on their relative order, and every order pattern of 3 values (ties included) occurs in this range.
// K: 3
// NIN: 3
// D: 1
// ORIG: 0 2 0
// REF: 1 0 2
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
  int n1 = (int)V[0], n2 = (int)V[1], n3 = (int)V[2], small, out = 0, cnt = 0;
  if (CMP(H[0], n1, n2)) {
    small = n1;
    if (small > n3) { out = n1; cnt++; }
    else if (n3 > n2) { out = n2; cnt++; }
    else { out = n3; cnt++; }
  } else {
    small = n2;
    if (small > n3) { out = n2; cnt++; }
    else if (n3 > n1) { out = SEL3(H[1], n1, n2, n3); cnt++; }
    else { out = SEL3(H[2], n1, n2, n3); cnt++; }
  }
  return cnt == 1 && out == ref_median(n1, n2, n3);
}
