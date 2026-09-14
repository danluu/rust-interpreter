# Next work

The scratch-value/scalar-call composition is adopted with exact measured tool
`df4006e0` / VM `6ac4dd9e`. All 726 project-history commands, five performance
guards and both 88-command full-parser guards pass. Token improves 6.30% wall
and 6.51% CPU but remains 1.571× ordinary native. Folded improves 3.11% wall;
pgrust, rg-aot and Nushell differences are within variation. The full parser
still loses to native. [Integration and limits](results/scratch-scalar-main-qualification-01/assessment.md).

1. The two adopted-VM captures are closed: all 1,561 / 1,231 generated self
   samples map to exact same-process schema-2 emission. Memory partitioning
   reconstructs every ordinary function and scalar body; payload loads account
   for 247 / 124 samples. These diagnostic windows establish no latency gain.
   [Samples](results/scratch-scalar-runtime-sampling-01/assessment.md),
   [memory parts](results/scratch-scalar-memory-parts-01/assessment.md).
2. The source/narrow-Copy observer passes 22 controls and exact reconstruction,
   but covers only 22 / 1 actual load samples. It stays parked. The scalar-aware
   protocol observer now reconstructs all 409 / 440 Call/Return samples exactly;
   ordinary frame clearing accounts for 89 / 62. The virtual-zero census admits
   15 more leaves but covers no current transition samples; eight controls and
   192 synthetic reference comparisons pass. Park that policy. The typed current-call join attributes 84 block transition samples to
   targets first rejected for unknown reads. The diagnostic
   read-only scalar graph passes 48 controls and admits 395 plans, covering
   42 transition / 53 body block samples and none in exhaustive. The native prototype passes 359 bytecode tests/profile after an uncovered
   heap-free ABI issue was corrected. Actual emission admits 392 functions and
   preserves all 71 existing scalar bodies byte-for-byte, covering 94 block
   samples. Immutable candidate cb47107b9d64 now passes 622 workspace tests/profile,
   407 Python tests (22 skips), 121 strict/cache commands and three original
   profiles against three exactly bound adopted controls. Token block scalar
   Calls rise by 7.73 million with exact logical counts, memory and entropy.
   Its complete primary fails (wall 0.999836, CPU 0.999544, wall A/A 0.019585).
   Park this revision and cancel larger comparisons. Its exact 199-body census
   finds duplicate reads concentrated in one callee. A subsequent structural
   census favors external-write leaves (153 block samples) over nested Calls
   (59), wider results (11) and cycles (5). The bounded private-store model
   passes 369 bytecode tests/profile and retains 138 block samples in 168 plans.
   Exact memory snapshots cover success, failure, branches and non-idempotent
   replay. The native backend retains 165 plans and all 138 samples, preserving
   71 adopted scalar bodies. Candidate 494c9f013bb5 passes 641 workspace tests
   per profile, 407 Python tests (22 skips), 121 strict/cache commands and three
   original profiles with exact counts/memory/entropy. Block scalar Calls rise
   from 11.23 to 27.65 million. Its 40-command primary fails: wall 1.000153,
   CPU 0.976356, wall A/A 0.068269. Park this revision and cancel larger histories.
   The exact 245-body store-cost census finds 32.94 million repeated containing
   write checks and fully overwritten publications on successful block paths.
   A separate store-log simplification passes 381 bytecode tests/profile (17
   ignored), including intervening aliases and later faults. Its immutable
   tool 5b86b3ab passes 644 workspace tests/profile, 407 Python tests (22 skips),
   121 strict/cache commands and three original profiles. Run the frozen
   40-command primary next; no larger histories have started.
   Main retains df4006e0; no gain is established.
   Retain earlier negative initialization/tree and wider-memory results.
   [Scratch coverage](results/scratch-source-census-01/assessment.md),
   [current protocol costs](results/scalar-protocol-census-03/assessment.md),
   [virtual-zero result](results/scalar-virtual-zero-census-01/assessment.md),
   [current callee costs](results/current-call-shapes-01/assessment.md),
   [read-only model](results/scalar-readonly-census-01/assessment.md),
   [native controls](results/scalar-readonly-native-controls-02/assessment.md),
   [native census](results/scalar-readonly-native-census-01/assessment.md),
   [build](results/scalar-readonly-native-build-01/assessment.md),
   [strict qualification](results/scalar-readonly-native-qualification-01/ASSESSMENT.md),
   [original profiles](results/scalar-readonly-native-profile-01/ASSESSMENT.md),
   [failed primary](results/scalar-readonly-native-screen-token-01/ASSESSMENT.md),
   [body census](results/scalar-readonly-shapes-01/assessment.md),
   [structural bounds](results/scalar-next-boundaries-02/assessment.md),
   [private-store model plan](benchmarks/experiments/scalar-transaction-model/PLAN.md),
   [model qualification](results/scalar-transaction-model-03/assessment.md),
   [native controls](results/scalar-transaction-native-controls-03/assessment.md),
   [native census](results/scalar-transaction-native-census-01/assessment.md),
   [immutable build](results/scalar-transaction-native-build-01/assessment.md),
   [strict checks](results/scalar-transaction-native-qualification-01/ASSESSMENT.md),
   [original profiles](results/scalar-transaction-native-profile-01/ASSESSMENT.md),
   [failed store primary](results/scalar-transaction-native-screen-token-01/ASSESSMENT.md),
   [store costs](results/scalar-transaction-costs-01/assessment.md),
   [store-log controls](results/scalar-store-log-controls-02/assessment.md).
3. Use the existing primary-first changed-source screen and all predeclared
   correctness/adoption guards. Preserve failures and noisy outcomes; do not
   retime unchanged parked candidates or reinterpret old gates. Reuse existing
   passing evidence only with complete relevant source/binary identity.
4. Keep compiler/Cargo/host-debuginfo/parser-exporter work in the other session's
   ownership. No duplicate budget-per-region implementation: ordinary native
   regions already precharge their static count. Do not infer safe native rlib
   reuse from metadata equality alone. Larger parser arenas remain parked.
5. Keep conservative resource admission. Recently retired caches stay retired;
   retained source/artifact snapshots, installed tools, shared ROOT build target
   and peer/private work are protected. Future cache estimation can use actual
   per-arm peaks in a new protocol, without weakening an existing reservation.

Runtime options remain explicit, guest fallback stays custom, and the saved
goal remains paused. Manual work continues. The September 13 12:45 suggestions
are unchanged and their [review](docs/SUGGESTIONS-REVIEW-20260913-1245.md) still
applies. [Prior next-work history and parked candidates](docs/history/RUNTIME-NEXT-20260914-before-scratch-scalar-integration.md).
