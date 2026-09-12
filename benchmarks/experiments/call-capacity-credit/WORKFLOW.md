# Four-mode capacity-credit runtime experiment

Candidate tool `2ad48ea7fd0d0c8a5d32e220b9c3997684d9952f13b8acd348fc59c3a6d026c3` has VM `d26b6edf8667eb8143a570de996b9f23356229e5621ed93b48960c73e94c08ef`.
The runtime source is `024edc438d958ae7813fc728f48acc0e4c98684e` and passes 422 Rust tests in
each profile, one ignored. A test-only expansion additionally requires both
fast and checked capacity paths for every scalar layout; its four tests pass
in both profiles, with all production sources and installed VM unchanged.
Seven exact selections, nine suite commands and 203 strict native/cache checks
pass. The new driver is qualified before taking any performance sample.

Baseline and its A/A duplicate use integrated tool49746a22. Candidate and
baseline have identical exporter/wrapper binaries, including main's compiler
reuse. This isolates capacity credit; the fixed selected-suite anchor remains
fe9dcae0 and separately measures the complete experimental stack.

Modes in the four-order schedule are 0=integrated baseline, 1=its identical
A/A duplicate, 2=capacity-credit candidate, 3=fixed selected-suite anchor.
Orders are 0,1,3,2; 1,2,0,3; 2,3,1,0; 3,0,2,1. Every mode occupies each position
once in four consecutive edited states; all ordered adjacent pairs appear
once. Fifteen edited states leave one incomplete block. Original/wrong states
use the same schedule separately. Native repository and line-tables controls
alternate before/after the custom group; check is last. Each mode has its own
fresh cache namespace and receives all source states, including restoration.

The driver freezes source pins, original test catalog, all code/plan/proof
inputs, exact installed binaries and source files. It requires build, seven-
test execution, nine-command suite and203-command native/cache qualification
before taking any sample. It checks the same original test outcomes, strict
checking, exact runtime limits and unchanged test source. All three cached
custom modes must export identical bytecode and catalogs for every state.

The policy in PLAN.md is prospective: fifteen complete pairs per comparison,
fifteen A/A pairs,154 commands per case. Token is primary; folded and pgrust
are mandatory guards even when the primary misses its performance gate.
Unexpected command/outcome/provenance failure stops the controller. No automatic
retry or partial result splicing; preserved timing noise is not a failure to
be rerun. No selection change, unchanged builds or entropy instrumentation
enters the latency sample. Two Cargo workers and two prepared custom workers
remain explicit; native uses ordinary libtest concurrency.
