# Bounded leaf placement diagnostic

All 17 tests and both exact profile reconciliations pass. The unmodified diagnostic
pass reproduces the integrated library's transformed Program byte-for-byte on
both inputs. These are already optimized artifacts; the baseline below is a
second pass and is not credited to a future candidate.

| Policy | Folded selected dynamic calls | Token selected dynamic calls | Token new clearing invocations |
| --- | ---: | ---: | ---: |
| Unchanged second pass | 0 | 1,733,361 | 0 |
| CompareBytes + entry-prefix, old caller guard | 175 | 18,341,542 | 12,856,005 |
| CompareBytes + entry-prefix, runtime caller guard | 15 | 10,081,209 | 0 |

Token added operations are 2,229 / 7,103 / 5,683 respectively, under unchanged
bounds. The old guard misses an actual runtime regression: inlining the
nonoverlap leaf grows its caller from 209 to 293 registers and changes it from
no clearing to clearing on 12,046,753 direct invocations. The runtime guard
correctly rejects that expansion. The slice comparison can inline into its
straight-line wrapper without newly required clearing.

Next implement and qualify a bounded definite-initialization proof shared by
runtime and inliner, then remeasure placements. Every read must follow a write
on every reachable path; aliases read before outputs, loops cannot assume their
first iteration is initialized, and exhaustion conservatively requires clearing.
No guest execution or production change occurred. Counts do not predict speed.
