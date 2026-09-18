# Scratch-memory values: primary passed; full comparison pending

The closed 40-command changed-source primary passes its existing admission gate.
Median paired candidate/control wall is **0.950873** (4.91% lower) and CPU is
**0.949951** (5.00% lower). The wall A/A envelope is **0.042955**, leaving a
**0.993828** wall margin: a narrow pass, not sufficient evidence for adoption.
CPU plus its envelope is 0.960470. Candidate/native wall is 1.558153.
Only the five valid edited states enter these ratios. Original, intentionally
incorrect and restored source states qualify behavior and cache transitions.

All 12 selected tests have matching native assertion outcomes in all 40 commands;
the incorrect edit fails as expected, source is restored, and candidate/control
bytecode matches. The exact tool df4006e0 / VM 6ac4dd9e passes 608 workspace tests
per profile, five focused scratch-memory controls per profile, 121 strict
Cargo/cache commands and six original profiles with exact logical counts, memory,
entropy, per-PC counts and operation maps. Closure verifies 1,669 evidence files
and 56 retained artifacts. No strict type or borrow checking is deferred.

The runtime reuses exact eight-byte local values already in x9 after address
handling, with bounded overlap and register-clobber invalidation. The candidate
also includes the previously parked scalar private-transfer composition. This
screen compares the complete candidate against matched adopted runtime; it does
not isolate the scratch cache's marginal effect from those other runtime changes.

Nested descriptive stages show Cargo -94.2 ms, build-to-ready -93.3 ms and
execution -172.6 ms. These overlapping medians do not add or establish causes;
the runtime change does not explain the observed Cargo variation.

Proceed to fresh three-cycle full histories, primary token first, then folded,
pgrust, private rg-aot and Nushell last under its separate disk admission. Require
13 selected/prepared compatibility commands and the frozen full-protocol checks
first. All full gates, 114-test parser compatibility and the edited-parser
comparison remain required. Keep production changes off main until then.
Completed screen compiler intermediates may be retired under the existing
retention policy, with all executable/artifact/source evidence preserved; its
warm caches are not inputs to the fresh full comparison.
