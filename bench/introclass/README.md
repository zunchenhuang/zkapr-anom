# IntroClass benchmarks (real bugs with student fixes)

Adapted from IntroClass (Le Goues et al., TSE 2015), https://github.com/ProgramRepair/IntroClass,
BSD 3-clause license (see LICENSE-IntroClass). Each file names the student repository, the buggy
revision, and the fixed revision it comes from.

Selection: in every student history of median, smallest, and grade, we took the first revision that
passes all tests after a failing revision, and kept pairs whose fix changes only numeric constants,
comparison operators, or variables (11 pairs). Three were excluded because the computed value was
already correct and only an output message changed, leaving 8 bugs.

Adaptation: scanf inputs become IN[], printf of the result records the output; the property is
equivalence with the IntroClass reference implementation. Holes: CMP(h,a,b) selects a comparison
operator, SEL3/SEL5 select a variable, H[i] replaces a constant; ORIG/REF are the student's buggy
and fixed values. Modeling steps, documented in each file: inputs range over {0..n-1} (the programs
only compare and copy inputs, so outputs depend only on their relative order, and every order pattern
of n values occurs in that range); inputs are masked so that unused bits are constants; grade's float
values are modeled as int (integer percentages, comparisons only); the uninitialized array of
ic_smallest_2 is modeled as further inputs.
