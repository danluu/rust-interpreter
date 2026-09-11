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
| Broadest fresh replay (`0e94d6d8`, experimental resumable calls) | 382 fre bodies passed, 7 ignored, with explicit options; not libtest |
| Main gaps | Compute performance, native configuration qualification, reuse, real unwinding, threads/OS/FFI and complete test-harness semantics |

## Run a selected function or test

Use `nightly-2026-09-08` with `rustc-dev` and `rust-src`. Dependencies must be
available locally; the launcher builds offline. On the qualified macOS host:

```sh
python3 scripts/prepare.py pgrust
python3 scripts/interpreter.py --manifest-path .work/sources/pgrust/Cargo.toml --package hashfn --entry murmurhash32 --engine jit -- 123
```

For a library test body, add `--test-body` and pass its qualified name to `--entry`.
Repeat `--entry` to batch zero-argument bodies returning unit or `Result<(), E>`.
Use `--engine interpreter` for the reference engine. Some standard-library paths
require `--std-mir`, which prepares a reusable metadata sysroot.

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
python3 -m unittest discover -s tests -p test_workflow_measurements.py
python3 scripts/update_status.py
```

Serialize task builds and benchmarks with `.work/benchmark.lock`. Current runtime
source `aa2f6ea` / tool `0e94d6d8` passes 276 workspace tests in debug and release,
with one ignored diagnostic. Its experimental resumable execution passes 47,004
fresh native-differential validation commands, 245 TLS/destructor commands and
382 fre body replays (seven ignored). Complete edited commands improve 21.82%
on folded trie and 33.09% on token phrase against the original JIT baseline;
both still lose to native Cargo. Fresh Nushell type-relations, Ruff and Nushell histories
pass their regression guards; four required cases remain before retention.
The new options stay disabled by default.
[Workspace validation](results/resumable-copy-release-01/assessment.md),
[fresh replay](results/resumable-copy-fre-01/assessment.md),
[performance decisions](results/resumable-copy-original-e2e-01/assessment.md),
[current work](STATE.md).

The benchmark harness replays actual source edits, preserves original tests,
requires a wrong edit to fail, and supports repeated cycles with child CPU
accounting. The stronger-native corpus completed 756 commands across nine
workflows, including 189 independent checks. Repeated fre source states exposed
compiler-cache-history artifact differences, retained alongside the timings.
[Protocol](BENCHMARKING.md), [token reproducer](benchmarks/TOKEN-PHRASE.md),
[repeated-run assessment](results/paired-repeated-token-01/assessment.md).

Read [ARCHITECTURE.md](ARCHITECTURE.md) for mechanisms and limits,
[RUNTIME-NEXT.md](RUNTIME-NEXT.md) for the next experiments,
[CHANGELOG.md](CHANGELOG.md) for checked-in changes, and
[results/INDEX.md](results/INDEX.md) for current evidence.
The [build index](benchmarks/tool-builds.json) maps source commits to exact tool
keys and verified binary hashes; regenerate it with `python3 scripts/tool_source_index.py`.

Every suggestion from the external review has an explicit
[decision](docs/SUGGESTIONS-REVIEW-20260910.md). The original
[plan](PLAN.md), [five persona rounds](persona-reviews.md), earlier
[native-cache/publication results](RESULTS.md), and
[implementation history](docs/history/README-20260910-before-review.md) remain
available. Unchanged-build publication savings are separate from edited builds.
