# Byte-phi primary fails; candidate parked

All 40 changed-source commands preserve the 12 original tests, wrong-edit
failures, five valid edited pairs, bytecode/catalog identity and source
restoration. Normal OS entropy, two Cargo/prepared workers and the 16 MiB arena
are unchanged. Both current arms use the adopted memory/Call admission.

| Measure | Candidate / adopted baseline |
| --- | ---: |
| Paired median wall | 1.010856526 |
| Paired median child CPU | 0.996383767 |
| Maximum absolute A/A wall deviation | 0.049636636 |
| Maximum absolute A/A CPU deviation | 0.012002070 |
| Wall ratio plus A/A deviation | 1.060493162 |
| CPU ratio plus A/A deviation | 1.008385837 |
| Candidate / ordinary native wall | 1.548342305 |

The gate fails; no speedup is established. Park immutable 7d80e36f and do not
repeat it or start larger project/parser histories. Main retains df4006e0.
Closure verifies 1,670 evidence files and 56 retained artifacts. The 424-byte
profile code reduction and passing controls remain valid structural/correctness
evidence, not evidence of an end-to-end improvement.

Descriptive stage medians are Cargo +41.0 ms and execution +1.6 ms. They are
nested/nonadditive and do not establish causal attribution. The prototype's
runtime savings are too small to justify adoption under the predeclared gate.

Shift investigation toward bounded scalar value optimization within ordinary
native regions. Census typed local-memory/value opportunities and original
sample coverage before implementing it. Distinguish this from the already
examined larger local register cache, region-entry facts and whole-leaf Calls;
retain all earlier negative results and preserve compiler-session ownership.
