# Build measurement controls

The launcher now records wall time and CPU through validated artifact readiness,
just before VM invocation. CPU includes its own user/system time and waited-for
build descendants. Cargo-only CPU is recorded separately. Startup/imports and
VM startup, decoding, validation and execution are outside this build boundary.
Normal launcher behavior is unchanged unless launch statistics are requested.

The paired workflow adds identical-build A/A controls with separate Cargo caches,
metric consistency checks, bounded benchmark-lock waiting and an explicit fresh
build/execution of restored original source. Listing and pre-VM failures do not
claim artifact readiness; a later VM failure retains the completed build timing.
The independent verifier recomputes paired values and checks recorded commands,
original assertions, source histories, output, cache identity and artifact hashes.

All83 Python tests pass, including12 metrics tests and15 workflow-control tests.
Both public A/A histories pass24 primary commands and8 independent Cargo-check
controls each;32 executed artifact copies across the two histories have matching
paired hashes. Every wrong production edit compiles and fails an original test.
Every mode freshly rebuilds and passes restored original source afterward.

| Identical-build control | Edited pairs | Median paired wall change | Wall range | Median paired CPU change |
|---|---:|---:|---:|---:|
| fre token |5|+2.871%|-6.439% to +6.020%|+1.714%|
| pgrust hash functions |5|-0.342%|-4.059% to +3.496%|-0.475%|

These values describe control variability, not a speedup or confidence interval.
The same installed compiler, wrapper, VM, options and common scripts serve both
arms. The source copies use the existing public pins, with ordinary Rust checking
and persistent function reuse disabled. Host-tool build and shared std-MIR setup
are outside the measured commands. Native and checking references remain distinct.

The prospective compiler screen was expanded before candidate build/timing to
three separately initialized, order-rotated histories on each workload. Its fixed
gates and subsequent public confirmations are in [the plan](prospective-plan.md).
Individual wall variation exceeded5%; no A/A value will be subtracted from later
candidate measurements. This qualification establishes measurement controls and
makes no general, cold-build, whole-command or unknown-holdout performance claim.

Raw commands, logs, source copies, executed artifacts and immutable tool/source
snapshots remain under task-owned `.work` paths recorded in qualification.json.
The compact [token](../build-aa-token-20260912-01/summary.md) and
[pgrust](../build-aa-pgrust-20260912-01/summary.md) reports retain all results.
