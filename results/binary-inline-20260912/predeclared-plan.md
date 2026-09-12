# Inline the existing integer operation helper

Fixed before source edits, builds or timing. The baseline is the now-qualified
complete scalar inlining implementation d2a2597, with immutable binary
complete-scalar-inline-vm, SHA256
d80780990ea38eceffb099a1494a20601adc1d5dabd038ff01a87e51eca4f7e3.
The current source is being merged with upstream documentation/tooling; no
upstream Rust source differs. Record the exact merged parent before building.

Add only #[inline(always)] to the existing public binary function. Its body,
width/error checks, integer/overflow semantics, checked operand accesses and
write ordering remain unchanged. This is distinct from the parked typed
arithmetic experiment: no arithmetic algorithm changes. The prior baseline
assembly still calls binary and transfers value, overflow and Result tag through
a stack buffer. Verify removal of that boundary and document dispatcher/stack/
executable size or spill changes. Do not infer speedup from assembly alone.

Use the fixed six public saved artifacts and six alternating pairs after a
warmup pair, running both interpreter and JIT. Require at least 5% median paired
interpreter wall gain on pgrust OR Ruff; neither compute interpreter may regress
more than 5% wall or CPU. Reject JIT wall/CPU regressions exceeding both 5%
median paired change and 5ms difference between the marginal medians. If the
screen passes, run the fixed five additional workloads with the same material
regression guard in both engines and ten native-oracle fixtures for correctness.
Match all outputs, instruction counts, peak guest memory and frozen inputs.
Do not rerun an unchanged failed candidate to cross a threshold.

Require all 297 workspace tests in debug and release (one ignored), including
native arithmetic oracles, overflow/division faults, aliasing, budget boundaries
and interpreter/JIT equivalence. No new tests for an attribute-only change.
Use the pinned nightly, isolated target and original shared benchmark lock.
The merged comparison runner retains both engines by default; freeze the exact
measured harness. No unrelated worktrees, workloads or caches are controlled.

Qualification covers saved-bytecode process runtime including startup only.
Full edit/build/test latency and unknown holdouts are unmeasured.

Exact merged source parent before edit/build: ad31f94557f2907f71f88ad411c3e9b37f1b598a.
