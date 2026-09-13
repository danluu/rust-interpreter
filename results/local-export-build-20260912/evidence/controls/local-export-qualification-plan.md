# Qualify general local exporter work reuse

This plan precedes integration, compilation, tests and performance measurement
of the source-only composition f06b582c300ddec56230d4c1a796f4c92bfe3ba3.
Its four additions to candidate4 reuse initialized local operand sizes, serialize
normal bytecode once, check chosen layouts without a temporary vector, and reuse
panic classification within one MIR block. Exact compiler source key is
14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75.
The independent manifest binds all146 inputs in installer order plus13 design,
fixture, toolchain and validator files. Preserve the original component branches.

Finish the candidate4 diagnostic before changing root compiler inputs: its
frozen plan checks those inputs before and after its history. Then apply only
the six new component/packaging commits over root17bd9ac, verify exact source
and fixture hashes, and freeze all core qualification controls before any tests.
From root, run the exact absolute-Python command recorded in
`local-export-qualification-commands.json` for `freeze_local_export_inputs.py`.
The macOS Python launcher rewrites argv[0] to its actual interpreter path, so
the planned command pins that observed executable path explicitly.
Wait for terminal exit0 before submitting any existing `run_locked.py` qualification
command. This small no-lock orchestrator runs the source freeze and control freeze
sequentially and records both child argv/PIDs/times plus terminal source/control
receipt hashes. It runs no build or test and never acquires the benchmark lock.
Preserve a failed freeze; do not admit a qualification workload after it.
`local-export-qualification-commands.json` freezes the five exact command vectors
and debug/release profiles, using the established candidate4 argv with new labels.
Final qualification requires the successful freeze to finish before every workload
starts, exact command/cwd/PID/timestamp receipts, and complete frozen-control proofs.
Keep candidate4 source/evidence and its unselected built VM retained.

Use the established nightly-2026-09-08 host setup: jobs2, locked/offline
dependencies, the owned .work/perf-general-20260912/target, debug/test debug=0
for debug tests, and ordinary release profile for release tests/build. The shared
wrapper sanitizes inherited options and disables incremental only for host setup.
Require408 passing Rust tests and1 ignored per profile: candidate4's400 plus
five serializer tests and three layout-verifier tests. Require those named new
tests and all12 candidate4 tests explicitly in the logs. Preserve any failure.

Install a fresh immutable bundle under the new source key. Select only the new
exporter; retain the published candidate3 VM03d401c1 and wrapper56fec5a3 exactly.
Record all newly built binaries separately and preserve the unselected VM before
any later target reuse. Compare against candidate3 keyeb91912d for adoption;
candidate4 is not adopted merely because it has passed correctness checks.

Run the full existing23727-command native/exporter/interpreter/JIT/rejection
suite with the new bundle. Its27 nonbinary inputs remain fixed except the
reviewed tests/local_layout_fixture.rs extension (old87e04585, newcc907e09).
The existing111 native seeds,225 local-layout commands and fixture entry names
remain unchanged; the extension adds widths, high bits, zero-sized values and
alignment checks within existing functions. Preserve raw command records,
top-level generated summaries, source inputs and terminal controller receipts.
Reconcile all23727 raw records with the summary; bind the raw records and any
commands.jsonl archive in the final proof map. Include every prebuild-control
entry, specifically the baseline tool and qualification receipts, rather than
only checking them transiently.
Restore the tracked top-level validation summary afterward, keeping its new
result separately. Common15 launcher/measurement scripts remain byte-identical.

Core qualification alone is insufficient for adoption. Before performance work,
complete a separately fixed supplemental protocol covering successful audit
exports and leaf inlining, the original cache/replay and strict frontend behavior,
and tests/panic_store_fixture.rs. Follow the reviewed composition plan for actual
same-block MIR evidence and argument-directed size8 Store-before-Trap data flow,
native post-panic storage, normal return and uncaught failure parity under both
runtime engines and both leaf-inlining settings. Preserve ordinary compiler
flags and error order; a fixture name alone does not prove this path was covered.

Freeze any later observations-off performance screen before running it, retaining
the existing5% primary build-readiness wall improvement floor, improving CPU,
regression guards, original/wrong/restored controls and all histories/outliers.
Instrumented diagnostics locate work and do not decide adoption or establish
holdout speedups. No runtime implementation or safety/validation limit changes.

All builds/tests/benchmarks use the existing shared lock and exact task-owned
paths. Bounded lock waits never control other windows, processes or caches. No
AWS service or paid offering is activated. This is unexecuted preparation.
