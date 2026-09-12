# Four-mode runtime experiment

The installed candidate is `8f1070dbaa634e2d8cb9ac44936ed4114af7e399834c16c6bec31df9e1934dc0`,
VM `4b6edd00fba47cb4caba5bc00dcf2c0d6c43b9b004db4e9b130332e1328e4b62`.
Build source is `63a0e6c013028afe12f9f4ea74048d7988fdca1f`, with395 passing
Rust tests in each profile. The runtime-only build retains the corrected
composition's exact exporter and wrapper; main's newer compiler optimization
is a separate future integration, never credited to this runtime comparison.

Modes in the four-order schedule are 0=corrected composition, 1=its identical
A/A duplicate, 2=call-protocol candidate, 3=fixed selected-suite anchor.
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
