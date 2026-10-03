// IntroClass median, student fe9d5fb933, buggy revision 002, fixed revision 008.
// Hole L1: right-hand side of `small = num2` in the else branch (buggy num2, fixed num1).
// Property: exactly one output, equal to the reference median.
// Inputs range over {0..2}: the program only compares and copies its inputs, so its output depends only
// on their relative order, and every order pattern of 3 values (ties included) occurs in this range.
// K: 1
// NIN: 3
// D: 1
// ORIG: 1
// REF: 0
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
  int num1 = (int)V[0], num2 = (int)V[1], num3 = (int)V[2], median, big, small;
  if (num1 >= num2) { small = num2; big = num1; }
  else { big = num2; small = SEL3(H[0], num1, num2, num3); }
  if (num3 >= big) median = big;
  else if (num3 <= small) median = small;
  else median = num3;
  return median == ref_median(num1, num2, num3);
}
