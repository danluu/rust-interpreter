# A custom Rust development engine

This project checks Rust with rustc, lowers selected MIR to its own bytecode,
and runs it in a custom interpreter or direct AArch64 JIT. The objective is faster
**edit → build → test** feedback on large Cargo projects.

It is a working experiment for selected functions and test bodies. It cannot yet
replace `cargo test` or run arbitrary Rust applications. The completed corpus
and current experiments show useful savings on frontend/link dominated test batches and a remaining
execution gap on compute-heavy tests. Alternative native linkers/backends remain
unqualified.
[Measured status and per-workflow results](STATUS.md).

| Area | Current state |
| --- | --- |
| Frontend | Pinned rustc; ordinary type and borrow checking by default |
| Guest backend | Our bytecode interpreter and direct AArch64 emitter |
| Native emitter platform | Apple Silicon macOS |
| Benchmark projects | pgrust, fre, Nushell, Ruff, private rg-aot |
| Qualified fre assertions (`9637b0ac`, explicit resumable calls) | 382 library bodies and 52 integration tests passed in separate qualifications; 7 library bodies ignored; full libtest remains open |
| Main gaps | Compute performance, native configuration qualification, reuse, real unwinding, threads/OS/FFI and complete test-harness semantics |

## Run a selected function or test

Use `nightly-2026-09-08` with `rustc-dev` and `rust-src`. Dependencies must be
available locally; the launcher builds offline. On the qualified macOS host:

```sh
python3 scripts/prepare.py pgrust
python3 scripts/interpreter.py --manifest-path .work/sources/pgrust/Cargo.toml --package hashfn --entry murmurhash32 --engine jit -- 123
```

For a library test body, add `--test-body` and pass its qualified name to `--entry`.
For an integration target, also add `--test-target NAME`. Use
`--test-body --list-tests` in place of `--entry` to list checked test names and
ignore/expected-panic attributes as JSON. Listing runs no test bodies and needs
no native test executable. Integration targets share dependency metadata while
each command selects its exact artifact.
Repeat `--entry` to batch zero-argument bodies returning unit or `Result<(), E>`.
For experimental test isolation, add `--engine jit --jit-resumable-calls
--isolated-batch prepared --suite-report NEW_FILE.json` with at least two entries.
To select tests automatically in that mode, replace the entries with
`--test-filter PATTERN`; add `--test-exact` for one complete name. An empty pattern
selects all ordinary nonignored tests in the chosen target. Matching happens in
the checked compiler invocation that exports them. A selected expected-panic
test, zero runnable matches or more than 256 matches produces an error before
execution. A single filtered test is supported.

Each test gets fresh guest memory, statics and TLS; compiled code is shared
within a worker. Add `--suite-workers 2` for concurrent isolated tests. The
default is one worker; each worker owns its JIT on its creating thread and has
its own code budget. Reports remain in selection order. Two workers passed the
[120-command source-edit screen](results/parallel-suites-edit-screen-01/summary.json).
Token wall time fell 34.3% versus one custom worker, using 3.2% more CPU;
folded and pgrust passed their guards. The candidate still took 2.216× its
two-process native control. That screen used isolated native tests; newer
engine comparisons also include ordinary Cargo/libtest concurrency. See
[current experiments](STATE.md). One custom worker remains the default.
All selected tests are attempted and reported, including after an assertion
failure. `--isolated-batch fresh` constructs separate JIT code for comparison.
Runtime limits apply to each test. This models independent executions;
ordinary libtest can share mutable globals. Ignore/should-panic/unwind/thread
semantics are not implemented by this mode.

Use `--engine interpreter` for the reference engine. Some standard-library paths
require `--std-mir`, which prepares a reusable metadata sysroot.

The qualified development configuration uses the memory-operand JIT, prepared
test isolation, two explicit workers, function reuse and cached toolchain
discovery. For the measured fre token selection:

```sh
python3 scripts/interpreter.py --manifest-path .work/sources/fre/Cargo.toml \
  --package fre-kernels --test-body --test-filter 'token_phrase::tests::' \
  --std-mir --engine jit --jit-resumable-calls --jit-persistent-registers \
  --isolated-batch prepared --suite-workers 2 --jobs 2 \
  --function-cache auto --toolchain-lookup cached --inline-leaves \
  --trap-unsupported-calls --run-try-callbacks --allocation-limit 150000 \
  --instruction-limit 100000000000 --suite-report token-suite.json
```

Type and borrow checking still complete before execution; cached discovery
only avoids repeated compiler-identity lookup. Defaults remain explicit in
this example. The five-case comparison passes all726 commands: token improves
18.35% versus its fixed custom anchor, but remains1.894 times ordinary native.
The rebuilt full tool passes428 Rust tests per profile,104 harness tests and
263 cache/Cargo/project commands. [Integration and exact identities](results/memory-lookup-main-complete-01/assessment.md).

Use `--workspace-cache-root EXISTING_DIRECTORY` to place project Cargo outputs
and bytecode sidecars on an existing scratch disk. The launcher creates a
marked namespace for this checkout, then separates tool builds and
`--cache-namespace` selections within it. Installed tools and standard-library
metadata stay in the repository. The default cache location remains
`.work/interpreter-workspaces`. This option creates no volume and moves no files.

For an individual saved test profile, invoke the VM with `--profile NEW.json
--profile-test EXACT_NAME --suite-catalog PROGRAM.rbc.entries.json PROGRAM.rbc`
and the desired engine/limits. Selection validates the original artifact and
catalog, preserves the bytecode file, and starts fresh guest/JIT state. Stderr
records the selection digests. This diagnostic does not model shared prepared
code across a suite; guest failures do not produce a complete profile.

Use `--select-test EXACT_NAME --suite-catalog PROGRAM.rbc.entries.json` to
execute one saved test without instruction profiling. It uses the same catalog
validation and fresh guest state. This also permits `--jit-code-dump DIRECTORY`
to capture the uninstrumented code for a selected test.

Engine differential tests include reproducible generated control-flow programs.
For a larger campaign, set `RUST_INTERP_DIFF_SEED` and `RUST_INTERP_DIFF_CASES`
(at most4096) when running `cargo test -p rust-interp-bytecode --test generated_cfg
-- --nocapture`. Mismatches save a bytecode reproducer and settings under
`.work/generated-cfg-failures`, or the explicit `RUST_INTERP_DIFF_OUTPUT` directory.

`--trap-unsupported-calls` permits export past specific unavailable calls; reaching
one still stops execution. `--run-try-callbacks` supports normal returns only,
not panic unwinding. Fre's broad replay requires `--allocation-limit 150000` and
the other flags recorded in its reports. These options do not provide general
FFI, thread, `should_panic`, or libtest support.

LLVM builds the host tools and native controls. Unsupported guest code has no
fallback to LLVM, Cranelift, Miri, or another execution engine.

## Develop and measure

```sh
cargo +nightly-2026-09-08 test --workspace --locked --offline --jobs 2
python3 -m unittest discover -s tests
python3 scripts/update_status.py
```

Serialize task builds and benchmarks with `.work/benchmark.lock`. The complete-workflow
anchor `5b2330c` / tool `9637b0ac` passed 289 debug and release tests (one ignored).
Current source also includes the separately qualified interpreter changes below. Aggregate-frame
reuse improves folded-trie edited commands 12.77% over the preceding compiler;
token regresses 3.70%, within its fixed 5% guard. All seven held-out workflows
pass their separate wall/CPU guards. Broad qualification passes 47,004 native
differential commands, 245 TLS/destructor commands and 382 fre bodies (seven
ignored). Runtime options remain explicit; whole-project compatibility is open.
[Integration](results/aggregate-integration-root-01/assessment.md),
[compiler comparison](results/aggregate-relocation-e2e-01/assessment.md),
[held-outs](results/aggregate-relocation-heldout-recovery-01/assessment.md),
[current work](STATE.md).

The benchmark harness replays actual source edits, preserves original tests,
requires a wrong edit to fail, and supports repeated cycles with child CPU
accounting. The stronger-native corpus completed 756 commands across nine
workflows, including 189 independent checks. Repeated fre source states exposed
compiler-cache-history artifact differences, retained alongside the timings.
The newer [integration-target pilot](results/fre-integration-edit-01/assessment.md)
measures five real edits at 0.816s custom versus 1.015s native (20.4% paired gain),
with 18 jobs on both sides. The [compute-heavy integration target](results/fre-integration-es8-edit-01/assessment.md)
takes 3.867s custom versus 1.449s native (2.678× paired). Execution remains the
main gap; the short batch does not establish a general speedup.
[Protocol](BENCHMARKING.md), [token reproducer](benchmarks/TOKEN-PHRASE.md),
[repeated-run assessment](results/paired-repeated-token-01/assessment.md).

General arithmetic and scalar-memory changes improve saved-artifact interpreter
execution about 12.7% on pgrust/Ruff and 14.6–20.5% on four additional Fre cases.
All 297 workspace tests pass in debug and release (one ignored), with JIT within
the regression guards. These runtime measurements exclude export/build costs.
[Runtime comparison](results/general-interpreter-20260912/assessment.md).

Keeping frame state across interpreter instructions adds 26.8% and 28.1% runtime
improvements on pgrust and Ruff relative to that VM. Five additional workloads
improve 15.2–29.4%; JIT stays within its wall/CPU regression guards. All bounds
checks remain. [Frame-loop comparison](results/same-frame-interpreter-20260912/assessment.md).

Inlining the complete checked scalar-memory path improves pgrust a further 6.7%
relative to that frame-loop VM, and four Fre cases by 2.1–5.0%. Other cases stay
within the regression guards; no general JIT speedup is claimed. Method bodies
and memory checks are unchanged. [Scalar inlining comparison](results/complete-scalar-inline-20260912/assessment.md).

Inlining the integer-operation helper then improves Ruff by 5.8%, pgrust by 3.0%,
and five additional workloads by 2.8–7.5% relative to that scalar-inlining VM.
Arithmetic semantics and checked register accesses remain unchanged; both-engine
regression gates pass. [Integer inlining comparison](results/binary-inline-20260912/assessment.md).

Read [ARCHITECTURE.md](ARCHITECTURE.md) for mechanisms and limits,
[RUNTIME-NEXT.md](RUNTIME-NEXT.md) for the next experiments,
[CHANGELOG.md](CHANGELOG.md) for checked-in changes, and
[results/INDEX.md](results/INDEX.md) for current evidence.
The [build index](benchmarks/tool-builds.json) maps source commits to exact tool
keys and verified binary hashes; regenerate it with `python3 scripts/tool_source_index.py`.

Every suggestion from the external review has an explicit
[current decision](docs/SUGGESTIONS-REVIEW-20260912-2210.md). The original
[plan](PLAN.md), [five persona rounds](persona-reviews.md), earlier
[native-cache/publication results](RESULTS.md), and
[implementation history](docs/history/README-20260910-before-review.md) remain
available. Unchanged-build publication savings are separate from edited builds.
