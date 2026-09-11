Historical snapshot before the linked-block qualification. See [README](README.md) and [current runtime work](RUNTIME-NEXT.md) for the selected implementation.

# Rust development engine experiments

Current development: [custom JIT and real end-to-end test results](JIT.md).
Latest qualified build: [nine production-edit workflows](results/e2e-call-copy-corpus-01/summary.md).

The latest [paired build/test comparison](results/paired-call-copy-e2e-01/summary.md)
isolates the call-copy change across four workflows using identical executed
bytecode: 17 of 20 pairs improve. Native remains faster for word64 and SHA-1.
The custom engines run selected existing tests in pgrust, fre, Nushell, Ruff,
and private rg-aot. Measurements include actual source edits, Cargo, compilation,
and test execution. Heap/SIMD support enabled rg-aot's test, whose edited commands
took about 0.17 s versus 0.48 s natively. Broader compatibility and runtime costs
are still under development; this is not a general Rust runtime yet.

The newer benchmarks change production bodies and keep existing tests unchanged.
Batching and reusable selection caches brought fre's three-test workflow to
about 0.72 s versus 1.29 s natively. Nushell's four-test workflow measured
0.42 s versus 0.64 s, using an optional reusable standard-library MIR build
that costs about 11 s to install. See [workflow results and setup costs](JIT.md).

Seven Nushell floating-point range tests now also run unchanged after five
production refactors: about 3.95 s with either custom engine versus 6.41 s
natively. This group works with the installed sysroot, avoiding the extra MIR
setup. The engine now supports scalar floating-point operations and sequential
atomics used by local Arc ownership; guest threading remains unsupported.
[Range workflow](results/e2e-workflow-nushell-float-default-sysroot-01/summary.md).

All fourteen Nushell type-relation tests now pass after five production edits:
**17.35 s native, 8.06 s interpreted, and 7.93 s with the custom JIT**
in the latest completed nine-workflow comparison. They retain
the original enum cross-product checks, hashing/deduplication, and 100-step
widening chain. Single-thread TLS resets between selected tests while ordinary
statics remain shared; TLS destructor registration is still unsupported. This
workflow uses the reusable standard-library MIR setup (10.997 s, excluded from
command times). Guest execution takes about 8–10 ms, so compilation dominates.
[Type-relation workflow](results/e2e-workflow-nushell-type-relations-call-copy-01/summary.md).

A broader [survey of 3,500 existing test bodies](results/lowering-audits-01.md)
now guides compatibility work. It distinguishes lowering from actual execution.
The resulting six-test fre class-sequence workflow measured 0.74–0.75 s per
production edit versus 1.32 s natively, with all original tests unchanged.

The expanded twelve-test fre word64 workflow exposes a substantial execution
cost. MIR inlining, JIT address propagation, and register reuse with proven
initialization, inlining the JIT transition helper, and emitting checked arithmetic
have reduced edited JIT commands from 13.164 s to about 3.08 s.
Native still wins at 2.11 s in the latest comparison. All modes retain the original exhaustive
tests and reject a deliberately wrong production edit. The optimized MIR
setting is explicit; ordinary frontend and overflow checks remain enabled.
[Initial word64 measurements](results/e2e-workflow-fre-word64-01/summary.md),
[latest word64 measurements](results/e2e-workflow-fre-word64-call-copy-01/summary.md).
All seven established workflows, the eightfold word64 configuration, and the
independent SHA-1 workflow passed the [same-build regression comparison](results/e2e-call-copy-corpus-01/summary.md).

An explicit eightfold MIR-inlining configuration reduced the word64 edited
command to **2.43 s JIT versus 1.69 s native** in the wrapper comparison. The latest
qualified comparison measured 2.98/2.97 s after further runtime changes; complete
commands also reflect compilation and host variation. Five alternating runtime pairs
measured 2.457 versus 1.711 s with the same VM and production source; guest calls
fell from 39.1 million to 17.4 million. Thresholds remain opt-in. All three configurations pass expanded native
differential checks. [Inlining comparison](results/mir-inlining-word64-01/summary.md).

An independent pgrust SHA-1 workflow retains both original tests, including the
million-byte reference vector. Five production edits pass at eightfold MIR
thresholds: **0.750 s native, 1.160 s JIT, and 5.245 s interpreted** per command.
Native still wins this compute-heavy workload. Assertions now execute inside JIT
regions; call transitions and argument copying remain substantial runtime costs.
[SHA-1 workflow](results/e2e-workflow-pgrust-sha1-inline8-call-copy-01/summary.md),
[runtime evidence](results/pgrust-sha1-runtime-01/summary.md).

Scalar constants now avoid temporary storage when only their value is needed.
Word64 interpretation improved from 17.86 to 16.95 s per production edit. A paired
comparison with the same VM binary measured 2.596 versus 2.547 s JIT execution;
complete JIT commands remained approximately flat. The change also fixes valid
wrapped constant-pointer relocations and passes 11,190 differential/rejection
commands plus 93 launcher checks. [Validation](results/scalar-constant-validation-01.json).

Checked division and remainder now use the custom emitter through 64 bits,
including explicit zero-divisor and signed-overflow errors. Five identical-artifact
pairs improved from 2.571 to 2.481 s; all seven production workflows and 11,865
differential/rejection commands pass. [Division validation](results/jit-division-validation-01.json).

Forcing the host JIT-entry wrapper to inline improves same-bytecode runtime by
about 7% at both default and eightfold MIR thresholds. All eight production
workflows, 21,927 differential/rejection commands, and 93 launcher checks pass.
The eightfold end-to-end median changed little (2.463 to 2.431 s), because
compilation also varies. [Wrapper validation](results/jit-entry-alwaysinline-validation-01.json).

Assertion emission and separate interpreter/JIT loop specializations improve
controlled runtime comparisons in both engines. All 58 bytecode tests, 23,277
native differential/rejection commands, 93 launcher checks, and nine production
workflows pass. [Runtime comparison](results/engine-specialization-runtime-01/summary.md).

A local-frame proof now avoids general pointer checks when copying call arguments
whose ranges are known. A balanced comparison favors applying it to both engines;
a JIT-only variant was slower. All nine production workflows pass, alongside
65 bytecode tests, 23,277 native differential commands, and 93 launcher checks.
Cargo variation can outweigh the runtime gain, motivating an interleaved full-command
comparison next. [Runtime selection](results/call-local-copy-runtime-01/summary.md).

The current prototype is a **custom Rust bytecode interpreter**, using rustc's
frontend and its own lowering and execution engine, with a direct AArch64 JIT
on Apple Silicon macOS. Actual body edits improved measured focused build/run
loops; longer compute loops expose interpreter costs. The original pgrust test
needed hundreds of milliseconds in the interpreter versus a few milliseconds
natively. The custom native tier reduces that cost. Neither engine currently
runs the complete applications or whole test suites.

Start with [the implementation, usage, comparisons, and next steps](INTERPRETER.md).
The default preserves normal rustc frontend checking. Separate experiments
compare partial call-graph checking with and without committed semantic caches.

The earlier Cranelift function-cache experiment did not demonstrate a consistent
warm-edit benefit. Its Cargo change helped unchanged executable publication;
that is a separate result. The remainder of this README documents that earlier
native path, with measurements in [RESULTS.md](RESULTS.md).

The initial corpus includes **pgrust, Ruff, Nushell, fre, and private rg-aot**.
Every source revision is pinned in [benchmarks/corpus.json](benchmarks/corpus.json).
Private source and detailed logs stay under ignored `.work/`; reports contain
aggregate measurements. Original working trees are never used for builds or edits.

The implementation adds a local storage adapter to Cranelift's existing
`Context::compile_with_cache` API. Cranelift owns the function-stencil/ISA/flags
key and reapplies the current function's relocation and source-location
parameters. The adapter checks payload integrity, publishes complete entries
atomically, treats unavailable/corrupt storage as a miss, and isolates backend
versions. The development launcher caches workspace crates; Cargo retains the
coarser artifacts for unchanged dependencies. Rust type checking, borrow
checking, constant evaluation, and ordinary diagnostics still run.

## Build and validate

The tested host is Apple Silicon macOS. LLVM and the experimental backend use the
same pinned nightly and LLVM-built standard library. Four Cargo jobs are used by
default. Installing this toolchain adds a dated toolchain without changing the
user's default.

```sh
rustup toolchain install nightly-2026-09-08 --profile minimal --component rust-src,rustc-dev,llvm-tools,rustfmt
python3 scripts/prepare.py cg-clif cargo rg-aot fre pgrust ruff nushell
python3 scripts/build_backend.py
python3 scripts/build_cargo.py
cargo +nightly-2026-09-08 test --workspace --locked
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/validate_codegen.py
python3 scripts/validate_launcher.py
python3 scripts/validate_publication.py
```

`prepare.py` uses sibling fre/rg-aot checkouts when available. Otherwise fre comes
from GitHub; supply `--source rg-aot=/path/to/private/checkout` for rg-aot. It
fetches pinned commits into task-owned directories and refuses mismatched or
unmarked snapshots. It does not reset, clean, or edit the source checkout.

Validation compares LLVM and cached Cranelift execution after callee rebinding,
layout/constant edits, source-location changes, and reverts. It covers generic
code, trait objects, closures, async polling, threads, TLS, drops, and C calls.
A second pass enables Cranelift's cache checker, which recompiles hits and compares
the complete generated-code structures. Invalid uncalled bodies and bad constants
must still fail compilation. This is an initial regression suite, not a proof of
compiler correctness or complete Rust compatibility.

The launcher integration test checks project rustflags, host build-script
unwinding, and preservation of application arguments. The pinned upstream
Cranelift backend cannot complete `--emit=link,llvm-ir`: it emits its own
disassembly but rustc expects an LLVM `.ll` file. The cache bypasses dump requests,
and validation records the same unsupported outcome with and without caching.

## Use on a workspace

From the workspace directory:

```sh
python3 /path/to/rust-interp/scripts/dev.py build
python3 /path/to/rust-interp/scripts/dev.py --preserve-executables run --bin your-app
python3 /path/to/rust-interp/scripts/dev.py --backend clif-cache --panic-abort build
python3 /path/to/rust-interp/scripts/dev.py --backend clif-cache --panic-abort run --bin your-app
python3 /path/to/rust-interp/scripts/dev.py --backend llvm test
```

The default is LLVM with normal panic behavior. Fast modes require explicit
`--panic-abort`: this backend build does not implement normal Rust unwinding.
That matters for applications such as pgrust, which uses unwinding for control
flow. Tests and release builds use LLVM in this prototype. A successful
abort-mode compile/startup benchmark does not qualify the program for normal use.
An explicit build with Cranelift's experimental `unwinding` feature also failed
the compiler probe on this host: its exception-table section was invalid for
Mach-O. LLVM passed that probe. The launcher does not enable that feature.

On the tested macOS host, `--preserve-executables` avoids replacing an executable
when its entire contents match Cargo's current output. Cargo still checks the
build normally. This uses a locally built, pinned Cargo without replacing the
installed Cargo or changing the compiler-artifact namespace. Symlinks, extended
attributes, differing permissions/ownership, changed bytes, and I/O errors take
the ordinary copy path. The option helps unchanged runs; it does not eliminate
linking or first execution of genuinely changed code. Its integrity checks and
launcher startup add overhead beyond the direct-Cargo benchmark measurements.
On the tiny integration fixture, the launcher added about 48 ms with LLVM and
102–105 ms with the Cranelift modes. For the native path with minimal wrapper
overhead, the same Cargo experiment can be invoked directly:

```sh
RUST_INTERP_PRESERVE_EXECUTABLES=1 rustup run nightly-2026-09-08 /path/to/rust-interp/.work/cargo-build/release/cargo run --bin your-app
```

That direct command uses ordinary Cargo target-directory behavior. See the
[launcher overhead measurements](results/launcher-overhead.json).

Artifacts live under `.work/dev-targets/`, separated by workspace, compiler,
backend contents, and flags. The function cache persists across compiler
processes and application restarts. No application state is kept alive, no
daemon is installed, and no hot reloading is attempted. Total cache eviction is
not implemented yet; cached entries are limited to 64 MiB each. Monitor disk use
and treat this as an experimental local cache, not an untrusted shared cache.

## Benchmark contract

The harness uses serial builds and records load before and after each sample.
It does not stop, suspend, or reprioritize unrelated work. A file lock prevents
overlapping runs from this project. Timed builds use downloaded dependencies,
`--locked --offline`, explicit target directories, and four build jobs. They
preserve repository optimization and debug settings while explicitly controlling
incremental compilation. The first exploratory pass used `debug=0`; on macOS,
that also enabled a costly post-link stripping step, so those results are kept
separate. The compiler validation suite also exercises full debug information.

Each accepted sample includes a freshly launched program that must demonstrate
the expected edit, followed by a project-specific runtime check. No-op builds
must reuse Cargo artifacts; telemetry uses a new file per invocation so replayed
Cargo output cannot be mistaken for compilation. The initial edits are synthetic
body probes, not a representative history of real development. Cold observations
are reported separately from warm medians. Do not interpret startup checks as
full application or test-suite performance.

Detailed provenance, compiler output, process IDs, validation output, and raw
timings live in `.work/runs/<run-id>/`. `scripts/report.py RUN_ID` produces
reviewable aggregates under `results/`. Build failures remain in the raw data
and are excluded from speed comparisons. The private project's source and
compiler diagnostics are not copied to aggregate reports.

The next decisions should follow the measurements: improve cache locality only
where native generation is significant; investigate frontend/dependency
invalidation where it dominates; retain LLVM when the candidate loses the actual
edit/build/test loop. Demand compilation and interpretation come after these
baselines, with the Rust semantic boundaries preserved.

The broader design and the five rounds of adversarial review are in
[PLAN.md](PLAN.md) and [persona-reviews.md](persona-reviews.md).
