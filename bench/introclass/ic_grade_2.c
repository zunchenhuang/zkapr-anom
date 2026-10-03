// IntroClass grade, student bfad6d21d6, buggy revision 000, fixed revision 011.
// Hole L1: operator of `stuscore > thresha` (buggy >, fixed >=).
// Thresholds are strictly decreasing, as the assignment states. The program reads percentages as int
// and only compares them; on integer inputs int and int comparisons coincide, so values are modeled as int.
// Property: exactly one grade printed, equal to the reference.
// Inputs range over {0..4}: the program only compares and copies its inputs, so its output depends only
// on their relative order, and every order pattern of 5 values (ties included) occurs in this range.
// K: 1
// NIN: 5
// D: 1
// ORIG: 2
// REF: 3
// BIN: introclass
#include "_common.h"
static char ref_grade(int aval, int bval, int cval, int dval, int score) {
  if (score >= aval) return 'A'; else if (score >= bval) return 'B'; else if (score >= cval) return 'C';
  else if (score >= dval) return 'D'; else return 'F';
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
  int thresha = A, threshb = B, threshc = C, threshd = D, stuscore = S;
  char out = 0; int cnt = 0;
  if (CMP(H[0], stuscore, thresha)) { out = 'A'; cnt++; }
  if ((stuscore < thresha) && (stuscore >= threshb)) { out = 'B'; cnt++; }
  if ((stuscore < threshb) && (stuscore >= threshc)) { out = 'C'; cnt++; }
  if ((stuscore < threshc) && (stuscore >= threshd)) { out = 'D'; cnt++; }
  if (stuscore < threshd) { out = 'F'; cnt++; }
  return cnt == 1 && out == ref_grade(A, B, C, D, S);
}
