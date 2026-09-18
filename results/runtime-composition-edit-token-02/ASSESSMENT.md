# Full token history: runtime composition

The fresh 154-command history passes its original performance gate. Across
15 valid edited pairs, candidate/adopted wall ratio is **0.96769033** and child
CPU ratio is **0.96381150**: 3.23% lower wall time and 3.62% lower CPU. The
duplicate/adopted wall envelope is 2.728848%; wall ratio plus that envelope is
0.99497881. This is a narrow pass, not evidence that each component helps alone.
CPU ratio plus its 1.899119% envelope is 0.98280270. Candidate/historical-anchor
wall is 0.69755973, satisfying the separate anchor guard.

The candidate combines native indirect transitions, checked readonly scalar
leaves and successor-only spilling on the adopted scalar/scratch runtime. It
uses immutable tool45a1529e / VMfd21a46f; adopted and duplicate use df4006e0 /
VM6ac4dd9e. Exporter and wrapper are identical. Strict Rust type and borrow
checking finish before execution. All12 original token tests, wrong edits,
artifact/catalog identities and final source restoration pass.

Candidate/ordinary-native wall ratio is **1.59822459**. The remaining native gap
is substantial. These are complete changed-source commands with normal entropy,
two Cargo workers, two prepared workers and native libtest default concurrency.
Original, wrong and restored states are correctness controls, not latency pairs.
The earlier40-command primary and failed two-command setup contribute no pairs.

Supervisor runtime-composition-full-token-02 finished normally. The first
checkpoint of runtime-composition-full-02 verifies the original frozen plan,
all recorded artifact hashes, pinned clean workload source and121 Git-bound
controller/script inputs. This admits folded matching next; pgrust, private
rg-aot, Nushell and both114-test parser performance histories remain required.
The candidate remains experimental. No adopted runtime or performance margin
changes, and no prior rejected candidate is relabeled.

Machine-readable evidence: [summary](summary.json), [closure](closure.json),
[terminal receipt](terminal.json).
