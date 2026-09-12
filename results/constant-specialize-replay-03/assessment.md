# Park bounded shared-call specialization

The final prototype passes386workspace tests in debug and release and all34
original assertions in the saved real suites. It does not show a useful runtime
gain, so it remains off main and will not proceed to the real edit screen.

| Suite | Tests | Median paired wall ratio | CPU ratio | Original → candidate logical instructions |
| --- | ---: | ---: | ---: | ---: |
| token | 12 | 1.01574 | 1.01584 | 28,984,786,067 → 28,263,269,800 |
| folded | 18 | 0.99544 | 0.99549 | 4,139,250,391 → 3,984,155,365 |
| pgrust | 4 | 0.99552 | 1.00073 | 81,417,823 → 81,405,839 |

All three alternating pairs per suite use the exact retained VM and qualified
replay02 entropy tapes. There are21VM commands and3whole-artifact verification
commands. Outcomes, original test identities, entropy consumption and per-test
guest memory peaks match; each artifact repeats its own instruction counts.
No Cargo command or source edit is timed, and no complete-workflow performance
gate has been evaluated. The first token pair improves1.66%; the other two
regress about1.58%. Preserve the complete result rather than retiming it.

The final offline transform adds51/24/3clones and redirects1405/341/17static
sites in token/folded/pgrust. Token transformation costs68ms in one diagnostic
invocation. The CFG-ordering fix admits previously rejected bodies. A separate
byte-liveness proof removes valid unobserved frame writes, shrinking one common
179-operation callee to28operations. These reductions still do not provide
measured runtime improvement. Bytecode operation counts are insufficient to
choose the next change; the native emitter already simplifies some operations,
and these transforms retain original frame layouts and call boundaries.

Next sample the uninstrumented generated native code of the two dominant token
tests, using exact per-process code dumps. Current named-test selection requires
instruction instrumentation, so separate selection from profiling first. Use
the observed machine-code costs to choose a structural runtime change. Preserve
the prototype on `experiment/constant-call-specialization-20260912`; do not merge
its compiler passes or retry these variants as performance candidates.
