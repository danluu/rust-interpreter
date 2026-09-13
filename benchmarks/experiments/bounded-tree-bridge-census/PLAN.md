# Assess a bounded-tree bridge inside the current resumable engine

The call-cost census retains 433 / 499 transition samples among 1,651 / 1,439
generated-code samples. Initialization elision and same-region local overwrites
have insufficient measured coverage. Capacity-credit batching already has a
parked implementation. Do not recreate or retime those unchanged mechanisms.

The older standalone native-tree mode executes a completely supported, acyclic
direct-call tree after one conservative budget/storage admission. It avoids
some per-call descriptor publication and return lookup. The current engine
instead uses resumable descriptors at every Call. A bridge could admit selected
complete trees from a resumable Call while retaining ordinary fallback before
progress. It needs a new cursor/host ABI and is not enabled by combining flags.

First run the exact current `jit/trees.rs` planner and emitter support/local-fill
predicate on the saved adopted artifact. Reuse their actual source, including
8,192-instruction, 64-depth, 256 KiB frame-span and 65,536-register-slot limits.
Preserve every decline. Run the five existing tree-proof controls in both build
profiles. These include interpreter-only fixtures for padding/depth bounds;
there is no benchmark execution or machine-code publication.

Join typed function IDs and direct Call sites to the closed call-cost census.
Report eligible calls from eligible and ineligible callers separately, eligible
callee Call samples, and returning-function samples as a separate upper bound.
Do not double-count a nested edge as another whole subtree. Report tree bounds,
current native bytes and existing guarded-range use: the bridge must preserve
current body optimizations or account for their loss. Current code readiness,
available storage, added duplicate code and bridge costs remain unmeasured.

An implementation is conditional on broad coverage. It must preserve strict
checking, exact argument/result-copy order, padding, initial registers, guest
limits, profile counts and fault identity. Budget/storage/code admission must
decline before any progress. Internal errors must unwind bounded host frames
without pretending to be a resumable guest continuation. Ordinary calls, VM
entries, TLS/root completion and unprepared callees retain their current paths.
The current x22 budget, tree x22 register cursor, x19 cursor layouts, persistent
pairs and guarded-range fallback differ and require explicit adapters.

Keep one admitted workload, two Cargo workers, 45-second lock admission, 16 GiB
initial build space and 8 GiB per child. Use immutable diagnostic tools and the
existing shared target. Freeze artifacts, profiles, planner/support source and
historical result identities. Preserve other sessions, the paused goal and the
user's suggestions file. No subagents, guest LLVM/foreign interpreter or AWS.
