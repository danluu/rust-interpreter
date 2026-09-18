# Full token history passed; held-out projects remain

All 154 commands pass the three-cycle changed-source protocol and its original,
incorrect-edit and restoration checks. Across the 15 valid edited pairs, wall
candidate/control is **0.936992** (6.30% lower), CPU **0.934942** (6.51% lower).
A/A envelopes are 0.014128 wall and 0.024061 CPU; the unchanged margins are
**0.951120** wall and **0.959002** CPU. The primary full gate passes.

Candidate/anchor wall is 0.737616 and CPU is 0.729801. Candidate/ordinary-native
wall is **1.571393**, and candidate/native-line-tables wall is 1.761495. The
custom runtime still loses to native on this workload. These paired-ratio
medians differ from ratios of separately computed median command times.

The final audit verifies 122 retained artifacts and 1,795 unique frozen inputs,
all 12 selected assertions, candidate/control bytecode identity and source
restoration. Candidate is df4006e0 / VM 6ac4dd9e with scalar Calls enabled and
strict full compiler checks. It includes the scalar private-transfer base;
this composition comparison does not isolate the scratch cache's marginal gain.

The closed checkpoint admits folded matching next, followed by pgrust hash,
private rg-aot and Nushell under the existing resource and performance gates.
No completed case will be rerun. Complete and edited-parser qualification still
remain. This is a primary win, not a completed broad runtime adoption.
