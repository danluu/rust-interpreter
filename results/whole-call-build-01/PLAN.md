# Bounded whole-call expansion experiment

Control: integrated source `5b2330c`, tool `9637b0ac`. The two runtime check/cursor
experiments remain parked. Census 05 qualifies a bounded CFG initialization proof
and identifies a larger set of removable calls under existing size limits.

Build one isolated candidate with three connected changes:

* Retain the fast existing block/entry-prefix initialization proofs; on failure,
  try bounded definite initialization over the reachable CFG. Every read must
  follow a write on every path. All aliases read before writes, function entry
  is empty even with backedges, and any bound exhaustion requires initialization.
* Let the compiler use that same runtime proof, including its post-expansion
  guard, instead of the old block-only heuristic.
* Extend bounded body inlining to CompareBytes and at most one direct Call,
  relocating all operands. Nonleaf bodies require a fully known acyclic direct
  call closure; recursion, paths into cycles and unknown indirect closures are
  conservatively excluded. Retain the 192-op, 512-byte-frame, 256-register,
  128-byte ABI/copy and 50% program/4096-op caller growth bounds.

One bounded pass, static policy, no profile-guided specialization or changes to
MIR thresholds. Function IDs, indirect handles, cold assertions and original
call ordering remain. The result-copy forwarding proposal is deferred: this
experiment's generic expansion can handle those bodies. No guest backend change.

Qualify the isolated source in debug and release. Preserve original benchmark
assertions; update only the legacy unit test whose expected rejection is precisely
the new proven cross-block behavior, adding an observable value and runtime-proof
check. Add focused CompareBytes and nested-call relocation, aliasing, branches,
faults, profiles, exact budgets and exclusions. Check strict frontend rejection
and real artifacts before timings. Runtime and exporter change; rebuild both
and verify the unchanged wrapper rather than copying either changing component.

Then run fresh identical-tool controls and the same folded/token real-edit
workflows: three cycles of five edits, complete command wall/child CPU, independent
Cargo-check floors, wrong edits and source restoration. Native uses the established
18-job/O0/incremental/default-test-thread control. Do not pool phases or claim
the fastest possible native configuration. Artifacts must remain deterministic
within each tool; different compiler outputs are expected between tools.

Fixed primary gate: token paired wall ratio <= 0.90, CPU < 1, and wall gain greater
than its fresh A/A envelope; folded wall and CPU <= 1.05. A failed gate parks this
candidate without threshold tuning. Broader native/TLS/fre qualification and all
seven held-outs with separate 5% wall/CPU guards precede source adoption. Preserve
all failures and every pair. No full-libtest or arbitrary-codebase claim.
