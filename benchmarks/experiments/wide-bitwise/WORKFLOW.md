# Wide-operation runtime experiment

Candidate tool `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`
has VM `6e8ae8736030ce5e033513a96dbbdf6542b49311fd26826c854e49ee0fde4828`.
Source `bf4f9b65848df134ad326f5ad6fba0a6d299acfa` passes419 Rust tests per
profile, one ignored, plus102 harness checks, seven exact selections, nine
suite commands and203 strict native/cache checks. Require the three current
profile replays and qualification of this driver before performance samples.

Baseline and its A/A duplicate use integrated tool49746a22. Candidate and
baseline have identical exporter/wrapper binaries, including main's compiler
reuse. This isolates wide-operation emission; the fixed selected-suite anchor remains
fe9dcae0 and separately measures the complete experimental stack.

Modes in the four-order schedule are 0=integrated baseline, 1=its identical
A/A duplicate, 2=wide-operation candidate, 3=fixed selected-suite anchor.
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

The primary gate requires paired candidate/baseline wall below1−observed A/A
wall and candidate/anchor wall at most0.92. Both paired CPU ratios must be at
most1.0. A/A bounds are4% wall and3% CPU. Folded and pgrust require both wall
and CPU ratios versus baseline and anchor at most1.05, with the same noise
bounds. These gates are fixed before measurement; no per-component8% target
is added. Report per-test worker durations descriptively and the complete
command as the outcome. No new cache cleanup is necessary at current capacity.
