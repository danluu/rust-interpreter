# Custom Rust interpreter experiment

This page records the initial interpreter phase. Subsequent work includes a
custom AArch64 JIT and real edit-to-test benchmarks including launcher overhead;
see [JIT.md](JIT.md) for the ongoing implementation and current decisions.

The project now has its own MIR-to-bytecode lowerer and standalone execution
engine. It runs selected library routines from **pgrust, Ruff, Nushell, fre, and
private rg-aot**. The useful result is a reduction in measured **edit, build, and
run** latency for these focused workloads, with ordinary rustc frontend checking.
This is a working prototype for function and test execution, not yet an engine
for running these complete applications.

## Implementation and use

The optional `--trap-unsupported-calls` allows export past unavailable direct
foreign calls and the compiler's `catch_unwind` intrinsic. Execution evaluates
the operands, then stops if it reaches such a call. It never returns a fabricated
success or invokes a generic host fallback. Other unsupported Rust operations
still reject export, and partial frontend-checking modes cannot use this option.
Call-site reports are verified against the exact selected bytecode, including
configuration changes and reverts. The launcher and audit/replay tools preserve
the option and classify an encountered boundary as `runtime-unsupported-call`.

This adds 11 passing original fre tests and a production-edit workflow. For that
workflow, explicit `RUSTFLAGS=-Zmir-opt-level=3` reduces edited build/test time
versus level 1 in five paired comparisons. Keep MIR tuning explicit until broader
comparisons support a default change.
[Evidence and limits](results/unavailable-calls-capability-01/summary.md).

`crates/mir-export` uses the pinned rustc frontend to check Rust, resolve concrete
instances, obtain MIR and layouts, and lower the selected static call graph.
`crates/bytecode` implements register instructions, guest memory, calls, and
execution limits. Application execution uses this new engine. There is no
LLVM, Cranelift, Miri, or other interpreter fallback for unsupported application
code. The tools themselves are built with ordinary rustc; rustc still performs
compile-time constant evaluation, and Cargo build scripts/procedural macros use
their ordinary native execution paths.

On the tested Apple Silicon macOS host, with `nightly-2026-09-08`, `rustc-dev`,
`rust-src`, and dependencies already installed:

```sh
cargo +nightly-2026-09-08 build --release --locked --offline --jobs 4 \
  -p rust-interp-bytecode -p rust-interp-mir-export \
  --target-dir .work/interpreter-build

python3 scripts/interpreter.py \
  --manifest-path .work/sources/pgrust/Cargo.toml \
  --package hashfn --entry murmurhash32 -- 123

python3 scripts/interpreter.py \
  --manifest-path .work/sources/pgrust/Cargo.toml \
  --package hashfn --entry murmurhash32_inverse_roundtrips \
  --test-body --instruction-limit 1000000000
```

The first invocation prints `2235285516`. The second executes the existing
100,000-iteration hash round-trip test body; a successful unit return prints `0`.
`--test-body` directly invokes a library test function. It does not implement the
libtest harness, including `should_panic`, `ignore`, fixtures, or test discovery.
It is suitable for this selected ordinary assertion-based test, not a general
replacement for `cargo test`.

Test mode also accepts zero-argument functions returning the standard
`Result<(), E>`. A generated guest adapter interprets `Ok(())` as success and
stops the batch on `Err`, reporting the test name. The original function keeps
its aggregate return ABI. Error-value formatting/destruction after failure and
custom `Termination` implementations are not implemented. Native test-result
comparisons cover 14 cases; the launcher passes 93 checks, including batches,
body/layout edits, reverts, and non-executing audits.

For compatibility discovery, `--test-body --audit-entries names.json` accepts
a JSON list of up to 4,096 unique function names. It performs strict checking
and independently attempts each lowering graph, prints a JSON report, and
executes no guest code. Cargo tracks both the audit mode and selection file;
the report is associated with its exact metadata artifact. The optional
`scripts/audit_test_lowering.py` corpus wrapper verifies pinned sources and
native test-list provenance. See the [initial survey](results/lowering-audits-01.md)
and [Ruff after Result support](results/lowering-audit-ruff-02/summary.md).

Add `--retain-audit-bodies` to save independently validated programs from an
audit. Files are limited to 64 MiB each and 1 GiB per pack, named by selection
index, and hashed before publication. The launcher checks the hashes and the
manifest belonging to Cargo's selected metadata artifact, including cached
configuration reverts. It still executes nothing. See [audit retention](AUDIT.md)
for usage, checks, and the real Nushell collection.

The launcher accepts a Cargo library package, a unique function name or full
definition path, and integer inputs expressed as unsigned bit patterns. It
preserves Cargo features, flags, and development profiles. Use a typed Rust
adapter for other inputs. Its target directories are separate from native
builds, and its tools are versioned by their source and binary contents.

Bytecode is published alongside the exact `.rmeta` file that Cargo selects.
This matters when switching configurations A → B → A: Cargo may reuse A without
invoking the exporter again. Running a single "most recently exported" file
would then execute B. The launcher selects Cargo's matching sidecar, checks
compilation success, and refuses execution when the artifact is missing.
Invocations sharing a target and entry are serialized through execution.

## Results after real body edits

The final strict comparison used five distinct mutations of existing routine
bodies per case. Each edit had to rebuild the selected crate, change the
observable answer, and agree with the native implementation. Unchanged builds
are not included in these warm medians.

| Selected crate/routine | Native build | Interpreter build | Native build + run | Interpreter build + run |
|---|---:|---:|---:|---:|
| rg-aot duration conversion | 0.308 s | 0.199 s | 0.503 s | 0.203 s |
| pgrust hashfn | 0.170 s | 0.167 s | 0.382 s | 0.170 s |
| pgrust adt_numeric | 0.589 s | 0.446 s | 0.821 s | 0.450 s |
| fre word classification | 1.167 s | 0.818 s | 1.364 s | 0.824 s |
| Ruff ruff_linter/noqa | 2.877 s | 1.986 s | 3.122 s | 1.989 s |
| Nushell nu-parser/lexer | 0.586 s | 0.345 s | 0.782 s | 0.348 s |

[Full results and cold observations](results/interpreter-edits-02/summary.md).
The harness times direct Cargo commands and execution; the convenience Python
launcher's startup and tool-integrity checks are excluded. Each total is the
median of paired build/run observations, so component medians need not sum to it.
All 72 build/run observations passed their output checks. An
[earlier pass](results/interpreter-edits-01/summary.md) showed the same direction
of benefit, with different absolute timings on the shared host.

Two mechanisms contribute. Checking and lowering selected functions avoids the
native generation and linking needed for the comparison executable. It also
avoids first execution of a newly generated native file: the VM executable stays
the same while the bytecode and answer change. On this host, many newly generated
native executables took roughly 0.2 seconds on their first execution, then a few
milliseconds on subsequent runs. The responsible macOS subsystem is not proven.
The build-only columns show the benefit independently of that launch effect;
the smallest hash crate has little build-time benefit.

These are six selected routines, not measurements of whole-project test suites.
The harness checks the selected real library and dependencies through an
independent consumer, preserving relevant repository profile settings. The
consumer has its own fixed, offline-resolved lockfile; it is not a full-workspace
build with the repository's original dependency graph. The mutations are
compiler experiments, not upstream fixes or a representative developer history.
Source revisions, lockfile hashes, tool hashes, exact commands, and raw results
are recorded. Private repository checkouts and raw diagnostic logs remain under ignored `.work/`.
The source adaptations are restored after each case.

All observations come from one shared M5 Max macOS host. Builds are serial with
four Cargo jobs, dependencies downloaded, and no interference with other user
processes. Five edits and one cold observation per condition establish a
promising direction; they do not establish general speedups or statistical
confidence across machines and workloads.

## Three checking policies

I also compared the colleague's suggested semantic deferral with ordinary
checking while holding the custom execution engine fixed:

| Policy | Behavior | Status |
|---|---|---|
| Strict | Run normal frontend analysis, then lower the selected call graph and produce real Cargo metadata | Launcher default |
| Demand | Check global type/impl consistency and selected bodies; stop compilation early | Standalone partial-validation experiment |
| Demand with committed cache | Same partial checks, but finish and commit rustc's incremental query session | Standalone partial-validation experiment |

"Demand" here means the **statically selected call graph**, including its
branches, is checked before execution. It is not first-call JIT type checking or
runtime borrow checking. Both partial modes can accept errors in unselected
bodies that strict mode rejects. Their artifacts carry a partial-validation flag
and the VM prints a warning. They cannot be used as a Cargo wrapper or presented
as a successful check of the whole crate.

Simply returning early from the compiler left incremental sessions in working
directories. The committed variant owns the compiler context lifecycle, saves
the query data, and finalizes the incremental session without inventing native
work products or Cargo metadata. That made a measurable difference across edits:

| Case | Strict compiler | Demand compiler | Demand with committed cache |
|---|---:|---:|---:|
| rg-aot | 0.043 s | 0.036 s | 0.033 s |
| pgrust-hash | 0.023 s | 0.017 s | 0.017 s |
| pgrust-numeric | 0.215 s | 0.059 s | 0.059 s |
| fre | 0.688 s | 0.491 s | 0.406 s |
| Ruff | 1.707 s | 1.427 s | 1.231 s |
| Nushell | 0.108 s | 0.102 s | 0.082 s |

These are compiler-only medians after five distinct edits, using captured rustc
invocations and prepared dependencies. They exclude Cargo and dependency
preparation and must not be substituted into the complete-loop table. pgrust's
profile disables incremental compilation, explaining the absence of a cache
benefit in those cases. [Checking-policy experiment](results/check-policy-1788937571851475000/summary.md).

This demonstrates one way an early-exit implementation can lose warm reuse. It
does not identify what happened in the colleague's implementation, whose engine
and measurements are unavailable. The transferable conclusion is to measure
semantic cache reuse separately from deferred checking and deferred codegen.

For reproduction, `scripts/bench_check_policy.py` prepares exact compiler
invocations. Direct exporter experiments enable `RUST_INTERP_DEMAND_BODIES=1`
and optionally `RUST_INTERP_DEMAND_CACHE=1`, with a separate `-C incremental=...`
directory for each policy. Keep these experiments isolated from Cargo targets.

## Why retain a future JIT tier

The interpreter is much slower on long compute loops. With startup warmed,
131,072 routine calls took roughly 60–130 ms in the interpreter and
2–3 ms natively. The same engine can win a short edit/test loop and lose a longer
workload. The final pass reproduced this across 240 matched execution samples.
[Runtime scaling measurements](results/interpreter-edits-02/runtime.md).

The existing pgrust round-trip test makes this limitation concrete: its unchanged
100,000-iteration body took **3.85 ms natively versus 344.76 ms in the VM**
(five alternating execution samples after warm-up; compilation excluded).
Both passed. Interpretation added about 341 ms to this one test, which can
outweigh the build savings in a small crate. This is why the interpreter alone
is not a general development-mode replacement.
[Existing-test measurements](results/interpreter-project-runtime.json).

The next architecture should therefore combine:

1. **Strict incremental checking by default.** Preserve committed semantic work;
   use the explicit partial mode to quantify avoidable work and its diagnostic
   tradeoff, not silently weaken the default.
2. **Custom bytecode for short or infrequent work.** Keep fresh-process state and
   inexpensive startup. Bytecode is reusable across unchanged runs; current
   selected graphs are lowered again after edits. Function-level bytecode reuse
   and a resident frontend are not implemented.
3. **A small custom native tier for hot supported functions.** Start with the
   existing integer/call/memory instruction contract and an AArch64 baseline
   emitter. Count its compilation and dispatch cost in the selected test's total
   time. Persist relocatable code with compiler-derived dependencies, and compare
   compile-on-first-call with measured hotness thresholds. Promote only when the
   expected remaining interpretation cost exceeds compilation, loading, and
   native execution cost. This JIT is not yet
   implemented; no performance benefit is assumed.
4. **Expand compatibility against actual tests before expanding claims.** Heap
   allocation, native calls, unwinding, and library boundaries are substantial
   prerequisites for full applications. Add developer edit histories and longer
   tests from all five projects, then measure complete commands including the
   launcher. Retain native builds when they complete the task faster.

Compared with reusing an existing interpreter/JIT, the custom path costs much
more compatibility work and has less correctness history. It gives direct
control over execution overhead, artifact lifetimes, and tier transitions;
it also avoids paying for diagnostic machinery designed for a different purpose.
Reusing rustc remains valuable in either design. Deferred type/borrow checking is
an independent policy choice, not a property that a JIT automatically supplies.

## Validation and remaining limits

The differential suite covers integer widths through 128 bits, signed overflow,
recursion, generic calls, arrays/slices, structs/enums, constants, normal drops,
and memory copies. It compares 111 boundary/random inputs in each checking mode,
then exercises callee and layout changes using committed semantic caches. It
also tests compile-error rejection, unsupported features, overflow traps, and
corrupt artifacts. Separate launcher tests cover configuration reverts, source
edits, errors, recovery, and missing artifacts.
The [differential results](results/interpreter-validation.json),
[launcher results](results/interpreter-launcher-validation.json), and
[existing pgrust test result](results/interpreter-project-validation.json)
record the checks and locations of their raw evidence.

```sh
python3 scripts/validate_interpreter.py
python3 scripts/validate_interpreter_launcher.py
python3 scripts/validate_interpreter_project.py
python3 scripts/bench_interpreter_project.py
cargo +nightly-2026-09-08 test --workspace --locked --offline --jobs 4 \
  --target-dir .work/interpreter-tests
```

To reproduce the routine comparison with prepared corpus snapshots and a new
run identifier:

```sh
python3 scripts/bench_interpreter.py rg-aot pgrust-hash pgrust-numeric \
  fre ruff nushell --run-id your-new-run-id
python3 scripts/bench_interpreter_runtime.py --baseline your-new-run-id
python3 scripts/bench_check_policy.py --baseline your-new-run-id
```

The current target contract is little-endian 64-bit with alignment at most 4096
bytes; only Apple Silicon macOS has been exercised. Unsupported MIR or missing
dependency MIR is rejected before execution. The custom heap supports the
default allocator, Box, and exercised Vec/String paths. An optional `--std-mir`
installation supplies missing standard-library MIR without guest code generation.
Function pointers and virtual calls use checked guest function handles. The
dynamic-trait fixture covers borrowed/boxed objects, supertrait upcasts, aggregate
arguments/results, runtime layout, and destructor effects. Nested unsized fields
now preserve runtime size, alignment, packing, field offsets, and trait-object
upcasts; a separate native fixture covers nested prefixes and boxed destruction
in three optimization modes. Structural smart-pointer coercions now follow the
compiler's field layouts, including matching NotNull wrappers and preserved
allocator fields. Native comparisons cover NonNull, Arc/Rc and weak references,
Pin<Box<_>>, trait upcasts, a non-ZST allocator, and overlapping source storage
in three optimization modes with both sysroots. The Arc overflow helper's
pinned panic-only body uses the existing panic-as-trap contract, guarded by
the real alloc crate identity. This adds no thread or lock implementation.
[Nested-layout validation](results/nested-dst-validation-01.json),
[structural coercion validation](results/structural-coercion-validation-01.json).
Scalar constant value consumers lower directly to immediate registers. Calls and
other address consumers still receive storage, and indirect/slice constants retain
their allocation identity. Constant-pointer relocation offsets wrap to the 64-bit
guest width; actual accesses retain the VM's memory checks. Native differential
cases cover numeric bit patterns, static and function pointers, wrapped offsets,
and call storage. [Validation](results/scalar-constant-validation-01.json).

Read-only Rust statics, including cyclic references,
are copied into guest constant storage. Mutable and interior-mutable statics use
a separate permanent guest-storage prefix, including relocated references and
cycles. Each VM starts from fresh initializers; a selected batch shares its
statics. The single guest thread now has TLS initializer storage. A selected-test
root resets mutable TLS between tests while preserving ordinary process statics.
Lazy initialization executes Rust's own TLS body. TLS destructor registration
and guest threading remain unsupported. `#[track_caller]` uses an explicit hidden guest
argument and rustc source locations, including inlined and virtual calls.
[Native comparisons and launcher checks](results/caller-location-validation-01.json).

Intrinsics with a compiler-provided ordinary Rust body may now use that body
when rustc explicitly permits backends to do so. It is lowered and executed by
the custom engines; mandatory runtime shims still need explicit support.
Multiply-with-carry matches native Rust for all twelve integer types, including
128-bit high/low results, in three optimization modes with both sysroots.
[Intrinsic-body validation](results/intrinsic-body-validation-01.json).
Pointer masking uses the custom integer operations; public pointer methods keep
slice and trait-object metadata through their ordinary MIR.
[Pointer-mask validation](results/pointer-mask-validation-01.json).

The runtime now supports scalar `f32`/`f64` arithmetic, comparisons, bitcasts,
integer conversions, rounding, square root, `log10`, and integer powers. Floating
arithmetic currently stays in our interpreter even with `--engine jit`; the
surrounding supported operations use the custom native tier. Separate native
comparisons cover NaNs, signed zero, infinities, saturation, and integer-to-float
double-rounding boundaries. `f16`, `f128`, and unimplemented math intrinsics are
explicitly rejected.

Atomic loads/stores, exchanges, integer operations, compare-exchange, and fences
are supported for **one guest thread with exclusively owned guest memory**.
Checked sequential bytecode implements that execution; it is not a concurrent
atomic implementation. The native-comparison fixture covers integer widths,
orderings, pointers, `Arc` clone/weak references, and destruction. Rejection
checks cover invalid orderings, alignment, bounds, and read-only writes. Guest
threads, external shared memory, and signal handlers remain unsupported.

There is no general OS/FFI bridge, custom global allocator support, TLS destructor
registration, guest threads, or native unwinding. A narrow macOS
`CCRandomGenerateBytes` primitive validates the full writable guest range before
borrowing its host storage for CommonCrypto; `RandomState` and hashing still run
as guest Rust code. Foreign `abort` terminates the guest with a trap. Actual
foreign symbols and signatures guard these primitives; same-named Rust functions
retain their ordinary bodies. Bytecode version 5 records mutable TLS ranges.
Normal drops are implemented; panic traps
terminate the guest and do not unwind or implement `catch_unwind`. This is a
material limitation for pgrust, which uses unwinding for control flow.

After strict checking, lowering follows normal MIR control flow and concrete
enum layouts to exclude statically unreachable blocks. The enum proof is limited
to a same-block discriminant assignment into an integer temporary whose address
is never taken. Uninhabited variants and unwind-only cleanup paths do not expand
callees; valid reachable unsupported calls still reject the export. Native
differential checks cover signed enum tags, nested enums, TLS initialization,
and same-named foreign/Rust functions, with rejection checks for inhabited
payloads including `MaybeUninit<Infallible>` and references to `Infallible`.
[TLS qualification](results/single-thread-tls-validation-01.json) records 9,840
differential/rejection commands and 93 launcher checks. The resulting
[fourteen-test Nushell workflow](results/e2e-workflow-nushell-type-relations-01/summary.md)
passed five production refactors and the deliberate incorrect edit in every mode.

Guest addresses are offsets into checked byte storage and never host pointers.
Default limits are 64 MiB for guest bytes plus live register payloads, 100 million
instructions, and 4,096 frames. These are operational limits, not a complete host
RSS bound. The engine is for local compiler-produced artifacts; it is neither an
untrusted-code sandbox nor a Rust undefined-behavior detector. Strict mode retains
ordinary frontend checks but does not claim every diagnostic that native
code generation or full-program linking could produce.

`--inline-leaves` enables an experimental bytecode export pass intended for JIT
comparisons. It is disabled by default. Small scalar leaf functions, including
branches, can share a disjoint storage bank within their caller. The pass resets
that bank on each invocation and preserves argument-copy order, result copying,
cold checks and function identities. It caps growth and rejects expansions that
introduce whole-caller register clearing. The resulting artifact's instruction
count, frame addresses and memory requirements can differ from the default.
Cargo tracks the option; changing it rebuilds the selected crate, and older
installed tools without the capability refuse the request. Both engines may run
the exported artifact, but the runtime screen slightly regressed interpretation.
It passes all eleven production workflows and 231 supported ordinary fre tests.
Complete-command performance is mixed (35/55 paired wins), so it remains opt-in.
[Experiment status](RUNTIME-NEXT.md),
[option-enabled differential validation](results/leaf-inline-native-validation-01.json).

The subsequent native local-fill emitter is qualified across all eleven
production-edit workflows. With leaf inlining enabled in both compared builds,
it improves 14/15 compute commands and all 15 compute execution stages. The
inliner remains opt-in. Deterministic function-pointer body scheduling makes
unchanged-source export reproducible; every compared artifact pair is identical.
[Current runtime comparison](results/paired-jit-local-fill-corpus-02/summary.md).

The earlier Cranelift cache and unchanged-executable experiment remains documented
in [RESULTS.md](RESULTS.md). Its no-op result is separate from the edited-code
measurements here.
