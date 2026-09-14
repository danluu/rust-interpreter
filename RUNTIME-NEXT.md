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
2. Count a bounded extension to scratch reuse before implementing it: capture
   Copy source values as well as destinations, and allow narrow Copy uses of
   matching low bits. Query after address handling and only at loads still
   emitted by the adopted VM. Narrow Load results need a stronger zero-extension
   proof, so exclude them. Require exact original emission, alias invalidation,
   conservative register-clobber handling and original static identities.
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
