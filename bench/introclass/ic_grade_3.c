// IntroClass grade, student f5b56c79c6, buggy revision 000, fixed revision 013.
// Holes L1-L4: operators of `score > A`, `score > B`, `score > C`, `score > D` (buggy >, fixed >=).
// Thresholds are strictly decreasing, as the assignment states. The program reads percentages as int
// and only compares them; on integer inputs int and int comparisons coincide, so values are modeled as int.
// Property: the letter grade equals the reference.
// Inputs range over {0..4}: the program only compares and copies its inputs, so its output depends only
// on their relative order, and every order pattern of 5 values (ties included) occurs in this range.
// K: 4
// NIN: 5
// D: 1
// ORIG: 2 2 2 2
// REF: 3 3 3 3
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
  unsigned UA = V[0], UB = V[1], UC = V[2], UD = V[3], US = V[4];
  __CPROVER_assume(UA > UB && UB > UC && UC > UD);
  int A = UA, B = UB, C = UC, D = UD, score = US;
  char out;
  if (CMP(H[0], score, A)) out = 'A';
  else if (score < A && CMP(H[1], score, B)) out = 'B';
  else if (score < B && CMP(H[2], score, C)) out = 'C';
  else if (score < C && CMP(H[3], score, D)) out = 'D';
  else out = 'F';
  return out == ref_grade(UA, UB, UC, UD, US);
}
