// IntroClass grade, student 531924c091, buggy revision 001, fixed revision 002.
// Holes L1-L3: operators of `percent > d`, `percent > c`, `percent > b` (buggy >, fixed >=).
// Thresholds are strictly decreasing, as the assignment states. The program reads percentages as int
// and only compares them; on integer inputs int and int comparisons coincide, so values are modeled as int.
// Property: the letter grade equals the reference.
// Inputs range over {0..4}: the program only compares and copies its inputs, so its output depends only
// on their relative order, and every order pattern of 5 values (ties included) occurs in this range.
// K: 3
// NIN: 5
// D: 1
// ORIG: 2 2 2
// REF: 3 3 3
// BIN: introclass
#include "_common.h"
static char ref_grade(int aval, int bval, int cval, int dval, int score) {
  if (score >= aval) return 'A'; else if (score >= bval) return 'B'; else if (score >= cval) return 'C';
  else if (score >= dval) return 'D'; else return 'F';
}
static char user_grade(const unsigned *H, int percent, int a, int b, int c, int d) {
  if (percent < d) return 'F';
  else if (CMP(H[0], percent, d) && (percent < c)) return 'D';
  else if (CMP(H[1], percent, c) && (percent < b)) return 'C';
  else if (CMP(H[2], percent, b) && (percent < a)) return 'B';
  else return 'A';
}
static int prog(const unsigned *H, const unsigned *IN) {
  unsigned V[5];
  V[0] = IN[0] & 7u; __CPROVER_assume(V[0] < 5u);
  V[1] = IN[1] & 7u; __CPROVER_assume(V[1] < 5u);
  V[2] = IN[2] & 7u; __CPROVER_assume(V[2] < 5u);
  V[3] = IN[3] & 7u; __CPROVER_assume(V[3] < 5u);
  V[4] = IN[4] & 7u; __CPROVER_assume(V[4] < 5u);
  unsigned A = V[0], B = V[1], C = V[2], D = V[3], S = V[4];
  __CPROVER_assume(A > B && B > C && C > D);
  return user_grade(H, (int)S, (int)A, (int)B, (int)C, (int)D) == ref_grade(A, B, C, D, S);
}
