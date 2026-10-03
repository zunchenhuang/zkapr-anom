/* Shared helpers for the IntroClass benchmarks (adapted from IntroClass, Le Goues et al. 2015).
 * CMP selects a comparison operator: 0 <, 1 <=, 2 >, 3 >=, 4 ==, 5 !=, 6 <, 7 <=  (low 3 bits of the hole).
 * SEL3/SEL5 select a variable (low bits of the hole). */
#define CMP(h, a, b) ((((h) & 7u) == 0u) ? ((a) < (b)) : (((h) & 7u) == 1u) ? ((a) <= (b)) : \
                      (((h) & 7u) == 2u) ? ((a) > (b)) : (((h) & 7u) == 3u) ? ((a) >= (b)) : \
                      (((h) & 7u) == 4u) ? ((a) == (b)) : (((h) & 7u) == 5u) ? ((a) != (b)) : \
                      (((h) & 7u) == 6u) ? ((a) < (b)) : ((a) <= (b)))
#define SEL3(h, a, b, c) ((((h) & 3u) == 0u) ? (a) : (((h) & 3u) == 1u) ? (b) : (c))
#define SEL5(h, a, b, c, d, e) ((((h) & 7u) == 0u) ? (a) : (((h) & 7u) == 1u) ? (b) : (((h) & 7u) == 2u) ? (c) : \
                                (((h) & 7u) == 3u) ? (d) : (e))
