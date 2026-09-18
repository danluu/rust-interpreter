# Current adopted runtime: two retained native-PC windows

Both repaired captures pass with original assertions and zero JIT declines.
The analysis assigns all 1,933 block and 1,429 exhaustive generated-code self
samples. Copy has 466/234 samples, Call 390/334, Load 237/86, budget 184/80,
flush 122/120 and Return 120/168. Scalar bodies account for 65/126 samples.
Keep host, heap and post-execution diagnostic categories separate; inclusive
host categories must not be added to the disjoint generated-code counts.

The installed adopted VM is 6ac4dd9e, tool df4006e0. Its 214 archived Git build
inputs are verified independently of this branch's rejected experimental Rust
sources. The fresh control profiles supply static identities only. Both guests
use ordinary entropy; these partial perturbed windows are not latency evidence.

Closure verifies 50 frozen inputs and 72 evidence files. Analysis initially
missed its 45-second lock admission; the separate admission-failure receipt is
retained in results/adopted-current-analysis-admission-02. A later analysis-only
supervisor consumed the same two captures. Neither successful guest was repeated.
The first sampling study's Untagged-label failure also remains separately closed.

The next investigation is repeated cold exit code inside native functions.
Measure exact byte-identical fault/fallback tails and their reachability/branch
constraints before considering code sharing. Existing rejected address, budget,
spill and scalar compositions stay rejected. Static size savings would justify
qualification, not a speedup claim or adoption without changed-source gates.
