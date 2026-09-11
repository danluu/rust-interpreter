Historical snapshot before the linked-block qualification. See [README](README.md) and [current runtime work](RUNTIME-NEXT.md) for the selected implementation.

# Ongoing end-to-end development

The current experiment combines the custom bytecode interpreter with a direct
AArch64 JIT. Development is ongoing. The primary decision metric is now a real
edit-to-test command, including Cargo, the launcher, compilation, and execution.

The engine supports single-thread TLS, closure function pointers, and
structural smart-pointer coercions. All fourteen existing Nushell
type tests pass after five production refactors. The latest completed corpus
measured 12.086 s native, 7.443 s interpreted, and 7.102 s JIT median complete commands. Execution itself is only
8–10 ms; Cargo dominates, and the small interpreter/JIT difference is not an
isolated runtime result. TLS resets between selected tests while ordinary
statics persist. Destructor registration remains unsupported.
[Type workflow and cold/setup costs](results/e2e-workflow-nushell-type-relations-type-id-01/summary.md),
[qualification](results/single-thread-tls-validation-01.json).

An earlier compatibility expansion added mutable statics and
`#[track_caller]`. Fre's independent lowering audit grew from 79 to 127 of 389
bodies, and all twelve original word64 matcher tests now execute successfully.
Their exhaustive reference comparisons initially measured 13.164 s JIT,
27.465 s interpreted, and 1.707 s native per production edit. The guest executed
5.18 billion bytecode instructions; native test execution took about 0.21 s.

MIR inlining, register reuse with proven initialization, and JIT propagation of
constants and frame-relative addresses, followed by inlining the checked JIT
transition helper and emitting checked arithmetic, reduced the latest
edited-command median to 3.441 s JIT. The subsequent scalar-constant export change
measured 3.472 s JIT, 16.953 s interpreted, and 1.698 s native. Checked division
then reduced complete JIT commands to 3.330 s, versus 1.770 s native. Native remains faster for
this workload. The explicit `-Zmir-opt-level=3` setting retains development
profile overflow checks and ordinary frontend checking. Five production edits
preserve test source, and a wrong edit fails in every mode.
[Original word64 comparison](results/e2e-workflow-fre-word64-01/summary.md),
[latest comparison](results/e2e-workflow-fre-word64-jit-division-01/summary.md).

Separate threshold experiments preserve checking while raising MIR inlining
limits by 2×, 4×, and 8×. All three pass the original tests after five production
edits. At 8×, complete commands measured 2.463 s JIT versus 1.641 s native;
five alternating same-VM runtime pairs measured 2.457 versus 1.711 s. Calls fell
from 39.14 to 17.36 million, while generated code grew about 6%. These remain
explicit configuration experiments, with no global default change. The expanded
configuration validation and subsequent host JIT-wrapper qualification are
complete. [Full inlining evidence](results/mir-inlining-word64-01/summary.md).

The JIT now rematerializes known constants and local addresses within a
straight-line region. Proven accesses within the active frame use direct
addresses; other pointers retain dynamic checks. Values needed outside a
region, including loop-carried values, are spilled. Bytecode instruction
accounting is unchanged. Generated code shrank by about 70% on the recorded
word64 artifacts. The bytecode suite, native differential suite, and 93 launcher
checks pass. [Validation](results/jit-local-facts-validation-01.json).

All seven established workflows and a second word64 configuration now pass on
one frozen build with forced host-wrapper inlining. JIT/native edited medians
are pgrust 0.536/0.662 s, fre class-sequence 0.700/1.345 s, Nushell keywords
0.435/0.622 s, Ruff registry 2.824/5.461 s, private rg-aot 0.190/0.550 s, and
Nushell type relations 6.002/12.962 s. Word64 measures 3.087/1.601 s with default
MIR thresholds, or 2.431/1.687 s at eightfold limits. These remain focused tests
within larger workspaces.

Five identical-artifact pairs measured 2.458 versus 2.274 s at default thresholds
(four candidate wins), and 1.700 versus 1.579 s at eightfold limits (five wins).
Instruction counts, generated code size, and peak guest memory are unchanged.
All 21,927 expanded differential/rejection commands, 93 launcher checks, and
52 bytecode tests pass. The eightfold complete-command median remains close to
the earlier 2.463 s; compilation changes offset part of the runtime gain.
Nushell type timings rose for both native and custom modes; stage records put
the increase in Cargo, while guest execution remains 7–10 ms. Historical
command differences are not isolated effects of the wrapper.
[Complete common-build comparison](results/e2e-jit-entry-alwaysinline-corpus-01/summary.md),
[wrapper qualification](results/jit-entry-alwaysinline-validation-01.json).

The new independent pgrust SHA-1 workflow passes both original tests, retaining
the million-byte reference vector and incremental updates. After five production
edits, complete commands measure 0.781 s native, 1.255 s JIT, and 5.726 s
interpreted with explicit eightfold MIR thresholds. All modes reject the wrong
round constant. The wrapper improvement also holds in five identical-bytecode
pairs here: 0.812 versus 0.694 s. Native still wins; a separate profile records
17.96 million interpreted assertions, motivating the next JIT experiment.
[SHA-1 production workflow](results/e2e-workflow-pgrust-sha1-inline8-01/summary.md),
[paired runtime and profile](results/pgrust-sha1-runtime-01/summary.md).

TypeId constant lowering now retains the compiler's numeric hash fragments.
TypeId, Any, and error downcasts pass native differential checks; all 23,277
validation commands and 93 launcher checks pass. The refreshed full Nushell
audit remains at 162/279 lowerable bodies: seven TypeId blockers become OS or
TLS blockers. All nine production-edit regression workflows pass. This is a
compatibility prerequisite, with no new Nushell execution result yet.
[Validation](results/type-id-validation-01.json),
[audit](results/lowering-audit-nushell-09/summary.md),
[qualified common-build corpus](results/e2e-type-id-corpus-01/summary.md).

The first assertion-emission candidate improved JIT runtime but regressed
interpretation in controlled comparisons. Moving fault formatting to a cold
helper did not restore word64 performance and was rejected. The selected
follow-up keeps assertion emission and specializes the interpreter/JIT loops
separately. It improves interpretation by about 6–8% and JIT runtime by about
1–6% against the last qualified VM, winning every recorded pair. All 58 bytecode
tests, 23,277 native differential/rejection commands, 93 launcher checks, and all
nine production-edit workflows pass. The change is retained. Complete command
medians still favor native for word64 and SHA-1.
[Qualified production corpus](results/e2e-engine-specialization-corpus-01/summary.md).
[Selected follow-up](results/engine-specialization-runtime-01/summary.md),
[initial assertion regression](results/jit-assertions-runtime-01/summary.md),
[rejected formatter](results/jit-cold-failure-comparison-01/summary.md).

Local-frame argument proofs now bypass general pointer classification for proved
calls. Both-engine application wins the balanced runtime comparison; a JIT-only
variant regressed interpretation and was rejected. The selected build passes
65 bytecode tests, 40 old/new VM fixture commands, 23,277 native differential
commands, 93 launcher checks, and all nine production workflows. Complete-command
results still include substantial Cargo variation. Interleaved old/new build/test
commands now show 17 of 20 pairs improving across four workloads, with identical
executed bytecode. The extended launcher passes 99 checks.
[Paired complete-command comparison](results/paired-call-copy-e2e-01/summary.md).
[Runtime selection](results/call-local-copy-runtime-01/summary.md),
[qualified corpus](results/e2e-call-copy-corpus-01/summary.md).

The word64 group now also works with the installed sysroot after adding the
verified core integer panic helpers. That first complete-command comparison measured
4.736 s JIT, 17.665 s interpreted, and 1.643 s native, with cold commands of
8.412/21.832/7.073 s respectively. This removes the extra MIR installation
requirement for that workflow; it does not close the warm runtime gap.
[Installed-sysroot comparison](results/e2e-workflow-fre-word64-installed-01/summary.md),
[integer panic validation](results/integer-panic-validation-01.json).

A [separate CPU sample](results/word64-cpu-profile-01/summary.md) puts about a
quarter of MIR-inlined word64 samples inside generated guest code. The VM loop,
copying, register resizing, and JIT transitions account for substantial remaining
work. Absorbing branches into JIT region exits produced only a small change:
4.538 s per production edit versus 4.574 s after fallthrough-jump removal.
The sampled large VM-loop symbol is not solely branch dispatch.
[Branch comparison](results/e2e-workflow-fre-word64-jit-branches-01/summary.md).

The register initialization change preserves initialized backing elements across
calls. Functions whose registers are all written before being read within each
basic block skip repeated clearing; other functions retain initial-zero
semantics. Paired execution medians dropped from 3.734 to 3.147 s on identical
word64 bytecode. Unit, native differential, all 93 launcher checks, and the
six-workflow production corpus pass. Complete word64 edited commands changed
from 4.538 to 3.908 s; native still wins that workflow at 1.674 s.
[Register initialization validation](results/register-init-validation-01.json).

The subsequent [CPU profile](results/word64-cpu-profile-02/summary.md) led to two
copy experiments; both were removed after failing paired runtime comparisons.
Inlining the checked JIT transition helper was retained: the same-artifact
runtime median changed from 3.033 to 2.887 s, and complete word64 edited commands
changed from 3.908 to 3.705 s. Guest code and instruction counts are unchanged.
All six workflows, native differential checks, and 93 launcher checks pass.
[Transition-helper qualification](results/jit-entry-inline-validation-01.json).

The [five-project heap/SIMD comparison](results/e2e-tests-heap-corpus.md) is the
earlier common-build baseline. It includes separate successful first builds and
five actual source edits per engine. Edited interpreter/JIT/native medians are
0.912/0.630/0.635 s for pgrust, 0.714/0.719/1.342 s for fre,
0.357/0.353/0.615 s for Nushell, 2.526/2.695/3.831 s for Ruff, and
0.171/0.171/0.480 s for rg-aot. Pgrust's interpreter regressed after the heap
change; its JIT/native commands were approximately tied. A subsequent
[memory-helper change](results/e2e-tests-pgrust-memory-inline-01/summary.md)
reduced its interpreter/JIT medians to 0.873/0.620 s, with native at 0.662 s.
These small differences need to be read alongside the stage timings and shared
host variation.

The more representative fre workflow now edits production codec bodies and runs
three existing tests without changing their test code. The original one-entry
interface took about 2.1 s for three serial custom commands versus 1.3 s for
native Cargo. Batch entry selection reduces that to about 0.72 s while preserving
the same tests, ordinary checking, and production edits.
[Before batching](results/e2e-workflow-fre-sequential-02/summary.md),
[after batching](results/e2e-workflow-fre-batch-01/summary.md).

Repeat `--entry` together with `--test-body` to select a batch. The exporter
lowers a shared reachable call graph and adds an ordinary guest caller for the
selected zero-argument functions returning unit or standard `Result<(), E>`.
Result adapters stop on `Err` without formatting or dropping the error value. Duplicate selections, aliases
of the same function, and incompatible signatures are rejected. Batches stop at
the first failing test. They do not implement complete libtest attribute,
unwinding, scheduling, or reporting behavior. Launcher checks verify that a
failure in the second selected body is observed by both engines.

Cargo's `harness=false` library tests are also recognized through their
`--cfg test` compilation. The exporter preserves that mode, which lets a custom
attribute macro retain the actual test function. The 93 launcher checks cover
custom-harness batches, failure in a second body, selection changes, recovery,
switching back to the built-in harness, and host build-profile changes. Calling
a body directly does not reproduce a custom harness's setup, attributes, or
scheduling; selected workflows must establish that the body is meaningful on
its own. The latest checks also cover mutable static initialization/reset,
`Result` test adapters, caller-location source edits, and independent lowering
audits. [Validation records](results/caller-location-validation-01.json).

The launcher now shares one Cargo target directory across entry selections for
the same manifest, package, and test mode. The selected crate records
`RUST_INTERP_ENTRY` and `RUST_INTERP_ENTRIES` in rustc's dependency information.
Changing the selection therefore regenerates its bytecode while leaving checked
dependencies reusable. A lock covers compilation through execution so another
selection cannot replace its sidecar during a run. Validation switches between
functions returning distinct values without source edits, checks dependency reuse,
and covers feature/rustflag reversions, compile failures, and missing sidecars.
The changing-selection production benchmark reduced interpreter/JIT medians
from 4.192/4.239 s to 0.722/0.732 s; native measured 1.291 s in the follow-up.
[Separate selection caches](results/e2e-workflow-fre-selection-01/summary.md),
[shared selection cache](results/e2e-workflow-fre-shared-selection-01/summary.md).

The same production-edit driver now covers all four existing pgrust `hashfn`
library tests, preserving the original 100,000-iteration roundtrip workload.
Five cumulative refactors measured 0.602 s with the JIT, 0.837 s with
interpretation, and 0.649 s natively. This is the small hashfn crate's library
suite within the pgrust workspace, not all pgrust tests.
[Production-edit measurements](results/e2e-workflow-pgrust-batch-01/summary.md).

Nushell's four existing parser-keyword tests now run through five production
refactors with changing test selections. Edited-command medians were 0.420 s
with the JIT, 0.431 s with interpretation, and 0.640 s natively. The original
collection and string-search paths are preserved. They need `--std-mir`, which
builds a reusable metadata-only standard library from an owned source copy.
Its one-time installation took 10.997 s, including 9.185 s compiling metadata.
The empty-workspace-cache command times were 18.826/20.176/22.443 s for
JIT/interpreter/native; adding the separate MIR installation makes first use
slower than native in this run. Tool installation and downloads are excluded.
[Nushell production workflow](results/e2e-workflow-nushell-std-mir-01/summary.md).

`--std-mir` remains opt-in. Target crates receive only the metadata sysroot;
host build scripts and procedural macros use the installed native toolchain.
The launcher checks compiler identity and installed artifact metadata before
reuse. Its 48 integration checks include a real build script, a procedural
macro, selection and rustflag changes, and rejection of conflicting sysroots.
Neither engine executes guest functions through the native standard library.

Ruff's six existing `registry::tests` bodies now pass five production refactors
with changing selections. Full edited-command medians were 2.982 s with the JIT,
3.002 s with interpretation, and 5.449 s natively. Empty-workspace-cache commands
took 27.245/27.698/55.470 s respectively. The custom times exclude the same
10.997 s reusable standard-library MIR setup; even adding that setup leaves
first use faster in this run. These are six selected tests within a library
target containing 2,832 tests, not the full library suite or application.
[Ruff production workflow](results/e2e-workflow-ruff-registry-02/summary.md).

Reaching this group required guest vtables and virtual dispatch, immutable
statics, and the standard-library typed-swap and unpredictable-selection
intrinsics. These preserve their ordinary value/move behavior. The complete group executes about
72 million bytecode instructions and emits about 7.6 MB of custom native code.
Emission takes about 7 ms. Warm frontend time exceeds two seconds, making
frontend profiling the next performance investigation.

The [pass profile](results/frontend-profile-ruff-01/summary.md) measured 1.008 s
in macro expansion, 0.223 s in type checking, and 0.066 s in borrow checking.
Optimizing host build tools to level 1 reduced the macro-expansion phase to
0.756 s, close to level 3's 0.732 s with less first-build overhead.
[Level 1 profile](results/frontend-profile-ruff-hostopt1-01/summary.md),
[level 3 profile](results/frontend-profile-ruff-hostopt3-01/summary.md).

An uninstrumented rerun applied host optimization level 1 equally to all three
engines. Edited medians were 2.574 s JIT, 2.592 s interpreter, and 5.071 s native;
cold commands took 48.086/47.484/74.186 s respectively. Compared with the earlier
default-profile run, the additional cold cost is recovered after roughly 50
edits. This is an estimate from five samples per setting on a shared host.
The setting stays optional; existing project profiles remain the default.
[Complete-command comparison](results/e2e-workflow-ruff-hostopt1-01/summary.md).

Cargo's existing configuration works with the launcher:

```sh
CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL=1 \
CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL=1 \
python3 scripts/interpreter.py --std-mir \
  --manifest-path .work/sources/ruff/Cargo.toml --package ruff_linter \
  --test-body --entry registry::tests::check_code_serialization --engine jit
```

The private rg-aot workflow now also changes production code while preserving
its existing collection-boundary test and SIMD-enabled paths. Five refactors
measured 0.182 s with the JIT, 0.184 s interpreted, and 0.552 s natively. All
engines rejected a deliberately wrong production edit. Source, edit details,
and command logs remain under `.work`; the report contains aggregate outcomes.
[Private-project production workflow](results/e2e-workflow-rg-aot-production-01/summary.md).

Nushell's seven existing floating-point range tests now pass through five
production refactors: **5.087 s JIT, 5.173 s interpreter, 7.438 s native**. The
tests remain unchanged and all engines reject a deliberately doubled iteration
step. Cold commands are close: 66.429/62.072/66.067 s respectively, before adding
the custom modes' separately installed 10.997 s standard-library MIR. This
workflow's custom first use is therefore slower than native once that setup is
included. [Range workflow](results/e2e-workflow-nushell-float-ranges-01/summary.md).

The custom range batch executes only about 27,000 bytecode instructions. Its
whole VM subprocess takes 3–4 ms; the selected crate's frontend takes about
1.08 s and lowering about 30 ms. The remaining Cargo work includes a dependency
chain through `nu-command`, `nu-cli`, and `nu-test-support` that is invalidated
by edits to `nu-protocol`. Profile those compilation units before optimizing
floating-point machine code. The small difference between the custom medians
does not establish a JIT benefit for this batch.

Supporting this workload required our own `f32`/`f64` operations and numeric
conversions, plus sequential atomics for the engine's exclusively owned guest
memory. Floating operations currently remain interpreted even in JIT mode.
Both new differential fixtures match native Rust on 111 inputs per engine;
the tests cover numeric boundaries, atomic memory checks, and `Arc` ownership
and destruction. [Qualification](results/numeric-runtime-validation-01.json).
No guest threading or external shared memory is supported.

The same runtime build reran pgrust's production workflow, including its
unchanged 100,000-iteration loop: 0.620 s JIT, 0.871 s interpreter, and 0.655 s
native. The interpreter remains slower on this workload, while JIT restores
competitive complete-command latency.
[Pgrust follow-up](results/e2e-workflow-pgrust-numeric-runtime-01/summary.md).

`interpreter.py --timings` forwards Cargo's ordinary compilation timing report
option and still runs the selected test batch. All 60 launcher checks pass.
`scripts/profile_cargo_workflow.py` uses those reports across real production
edits, retaining each complete timeline. Unit durations overlap and must not
be summed as command time. See [Cargo's timing documentation](https://doc.rust-lang.org/nightly/cargo/reference/timings.html).

The numeric range workflow also passes using the installed sysroot; it does
**not** require `--std-mir`. With that default configuration, the five-edit
comparison measured **3.946 s JIT, 3.954 s interpreter, 6.413 s native**. Cold
commands took 56.548/54.402/66.528 s respectively, without extra sysroot setup.
Use this configuration for the range group. Native warm times also improved
between the two runs, so the entire cross-run reduction cannot be attributed
to the sysroot change. The new comparison still establishes a useful
complete-command advantage within its own run.
[Default-sysroot range workflow](results/e2e-workflow-nushell-float-default-sysroot-01/summary.md).

```sh
python3 scripts/bench_e2e_workflow.py --project nushell \
  --workflow float-ranges --batch --run-id your-new-run-id
```

The floating-point differential fixture also matches native Rust for 111 inputs
per engine with the installed sysroot. Broader `Arc` use can still require
`--std-mir`: its full fixture reaches the unavailable `alloc::sync::panic_arc_overflow`
helper, while the range tests do not. Keep MIR availability checks tied to the
actual selected execution graph. The earlier keyword and Ruff workflows still
require the extra MIR.

## First complete-command benchmark

`scripts/bench_e2e_tests.py` adds five deterministic regression assertions to the
existing pgrust `hashfn::tests::murmurhash32_inverse_roundtrips` test. Its original
100,000-iteration workload remains intact. Each engine must first fail a
deliberately wrong assertion, then rebuild and pass each edited test. Native and
custom commands use the pinned project workspace, lockfile, and test profile.
Source changes are confined to the owned snapshot and restored afterward.

| Implementation stage | Native command | Interpreter command | Custom JIT command |
|---|---:|---:|---:|
| Before JIT | 0.664 s | 1.167 s | — |
| First scalar JIT, original launcher | 0.665 s | 1.170 s | 0.948 s |
| JIT and direct library-test selection | 0.688 s | 0.820 s | 0.601 s |

Each cell is the median of five actual test-source edits. These are separate
serial runs on a shared host, not a confidence interval or whole-project test
suite result. [Baseline](results/e2e-tests-prejit-01/summary.md),
[first JIT](results/e2e-tests-jit-01/summary.md),
[launcher improvement](results/e2e-tests-jit-02/summary.md).

The fre `fre-kernels` codec boundary test now also runs unchanged in both custom
engines. Adding five regression cases while preserving its seven original
roundtrips produced these complete-command medians:

| Project test | Native | Interpreter | Custom JIT |
|---|---:|---:|---:|
| fre unsigned codec boundaries | 1.234 s | 0.685 s | 0.662 s |
| Nushell parser keywords | 0.633 s | 0.368 s | 0.356 s |
| Ruff rule documentation | 3.731 s | 2.506 s | 2.502 s |

[Fre measurements](results/e2e-tests-fre-01/summary.md). Both engines spend about
3 ms executing this small test; Cargo takes roughly 635–645 ms. The small
interpreter/JIT difference is therefore mostly compilation variation. This
test demonstrates a focused compile-time benefit, not a JIT runtime gain.

[Nushell measurements](results/e2e-tests-nushell-01/summary.md) preserve the five
existing positive keyword assertions and add distinct negative cases. Execution
takes about 3 ms in both engines; the primary saving is again compilation.
The ordinary `nu-parser` library-test target and workspace profile are used.
These are selected existing tests in real workspaces, not full application or
whole-suite measurements.

[Ruff measurements](results/e2e-tests-ruff-01/summary.md) retain the check of every
registered rule and add a different indexed-rule regression assertion for each
edit. This run includes the dependency-MIR policy described below. The custom
path spends about 2.46 s in Cargo and 6–7 ms executing. JIT emission takes about
1.2 ms for roughly 785 KiB of code, making it slightly more expensive than pure
interpretation for this test's short execution. Both engines finish the complete
command in about 2.5 s.

The first JIT cut execution from about 356 ms to 143 ms, but the complete command
still lost. Stage timings exposed a separate 290 ms `cargo metadata` query.
The pinned Cargo supports `cargo check --lib --profile test`, which checks
exactly the library test target. That removed the metadata query and the
ordinary-library check previously requested by `--lib --tests`. Validation now
includes renamed libraries, an invalid unrelated binary, an unrelated integration
test, and a distinct test-profile setting.

## What the JIT does

`crates/bytecode/src/jit.rs` emits AArch64 words directly. No LLVM, Cranelift,
assembler, or other JIT library generates application instructions. It compiles
straight-line scalar sequences, including integer operations, casts, small
copies, checked guest memory access, and region exits containing jumps or
switches with up to 16 cases. Switches compare all 128 bits in source order.
Calls, region dispatch, checked arithmetic that needs overflow results,
128-bit arithmetic, and other unsupported instructions stay in our own interpreter.

Generated functions receive the current guest memory and register pointers each
time they run. They retain no pointers across guest calls or memory growth. The
VM keeps its instruction, memory, and call-depth limits. Compiled blocks execute
only when the remaining instruction budget covers the whole block; the tail
runs through the interpreter otherwise.

Regions are capped at 1,024 bytecode operations. Ruff's six-test registry group
contained a large initializer whose memory-check branches exceeded AArch64's
conditional-branch range when emitted as one region. Bounded regions let the
same bytecode execute; a regression test exercises multi-megabyte generated
code, faults near the start/middle/end, and budgets crossing region boundaries.

On Apple Silicon, code uses `MAP_JIT`, per-thread write protection, and instruction
cache invalidation. It does not change system security settings. The implementation
follows Apple's [JIT porting interface](https://developer.apple.com/documentation/apple-silicon/porting-just-in-time-compilers-to-apple-silicon).
It is currently specific to this platform, and is for locally produced artifacts.

The pgrust test initially generated about 52 KiB of native code in 0.1 ms and ran
roughly 90 million of its 101 million bytecode instructions through that code.
Persistent native-code caching is therefore not the next priority: code emission
was a tiny fraction of the complete command. Rustc's committed semantic caches
remain in use. Larger native graphs may change that decision.

## Current next experiments

1. An early shared register-arena experiment passed differential checks but did not
   improve the then-selected pgrust command: JIT medians remained about 0.60 s. Execution
   decreased from about 145 ms to 122 ms while Cargo timings varied. It was
   reverted at that point. The subsequently enabled word64 workflow made
   per-call register allocation much more consequential, and a reusable stack
   is now implemented and qualified on that workload and the wider corpus.
   [Register-arena experiment](results/e2e-tests-jit-03/summary.md).
2. Run meaningful existing tests from fre and the larger projects. Record coverage
   failures and choose compatibility work from those failures. Heap allocation,
   integer SIMD, and iterator closure calls now enable rg-aot's selected existing
   test; these mechanisms still need broader coverage.
3. Reduce generated loads, stores, and redundant address checks using validated
   dataflow. Measure complete commands after each change. Keep the interpreter
   as a differential oracle and an execution option.
4. Expand the edit corpus beyond added regression assertions to production
   refactors and realistic multi-test workflows. Do not infer general usefulness
   from the pgrust result alone.

## Run and validate

```sh
python3 scripts/interpreter.py --manifest-path .work/sources/pgrust/Cargo.toml \
  --package hashfn --entry murmurhash32_inverse_roundtrips --test-body \
  --instruction-limit 1000000000 --engine jit

python3 scripts/bench_e2e_tests.py --modes native interpreter jit \
  --run-id a-new-run-id
python3 scripts/bench_e2e_tests.py --project fre --run-id another-new-run-id
python3 scripts/bench_e2e_tests.py --project nushell --run-id one-more-new-run-id
python3 scripts/bench_e2e_tests.py --project ruff --run-id a-ruff-run-id

python3 scripts/interpreter.py --manifest-path .work/sources/fre/Cargo.toml \
  --package fre-kernels --test-body \
  --entry determinize_state_codec::tests::unsigned_roundtrips_boundaries \
  --entry determinize_state_codec::tests::signed_roundtrips_boundaries \
  --entry determinize_state_codec::tests::malformed_and_one_below_refuse
python3 scripts/bench_e2e_workflow.py --batch --vary-selection \
  --run-id a-new-production-workflow-run

python3 scripts/validate_interpreter.py
python3 scripts/validate_interpreter_launcher.py
cargo +nightly-2026-09-08 test -p rust-interp-bytecode --locked --offline \
  --jobs 4 --target-dir .work/interpreter-tests -- --test-threads=1
```

Set `RUST_INTERP_LAUNCH_STATS=1` to record Cargo, execution, and launcher durations
on stderr. JIT statistics distinguish emitted code from instructions actually
executed natively.

The scalar differential fixture runs 111 inputs through both engines under each
of three checking policies, plus callee/layout edits. Heap and SIMD fixtures
each add 111 inputs under ordinary strict checking in both engines.
JIT-specific tests cover
integer widths and signs, casts, comparisons, shifts, rotations, unusual memory
widths, overlapping copies, memory faults, and instruction limits. This is
regression evidence, not complete Rust compatibility. The default frontend
policy still performs ordinary checking; partial-checking experiments remain
explicitly marked. Panic unwinding, general FFI support, complete libtest
behavior, and full applications remain unfinished.

Fre coverage required integer min/max intrinsics and the standard Result-unwrap
and slice-index panic paths. Panic calls still stop with a trap. Pure local
argument preparation immediately before recognized standard panic functions is
discarded, allowing unused `dyn Debug` panic arguments without claiming general
trait-object support. Calls that evaluate message arguments remain executable.
Checks cover successful unwraps, errors, slice bounds, and user functions whose
module names resemble the standard panic namespace.

Nushell required the `compare_bytes` intrinsic. The runtime checks both complete
guest ranges before comparing unsigned bytes, including when an early byte
already differs. Differential checks cover empty, equal, and differently
ordered slices; range tests cover invalid and overflowing addresses.

## Cross-crate MIR and function pointers

The wrapper now passes `-Zalways-encode-mir=yes` when compiling library
dependencies. Ordinary `cargo check` metadata can omit executable MIR, even for
functions that a selected test calls. This flag keeps dependency function bodies
available. It is appended to rustc arguments, preserving Cargo's configured
rustflags and target selection. Old wrapper installations have separate target
directories. The initial fre/Nushell measurements precede this change; follow-up
measurements include it:
[pgrust](results/e2e-tests-pgrust-mir-01/summary.md),
[fre](results/e2e-tests-fre-mir-01/summary.md),
[Nushell](results/e2e-tests-nushell-mir-01/summary.md).

Function pointers use tagged guest handles. The interpreter validates the
function index, argument sizes, and return size before an indirect call; it
never converts a guest function pointer into a host code address. Both engines
pass calls through constant tables, generic functions, selected callbacks, and
safe-to-unsafe pointer coercions, plus malformed-handle and layout tests.

Taking a function address preserves its identity without generating a body
unless a possible indirect call has a matching argument/result byte layout.
Unknown shim layouts are retained whenever any indirect call exists. This is
conservative with respect to the runtime's mandatory call-layout checks, and
also applies to later-discovered pointers and calls. It avoids unnecessary
panic-formatting expansion without silently omitting possible valid indirect
callees. It does not defer ordinary Rust checking.
Closure-to-function-pointer coercions and general virtual dispatch remain
unsupported.

## Heap, integer SIMD, and closures

Guest heap addresses use a tag distinct from function handles; the remaining
bits are offsets into an owned byte arena. The allocator tracks layouts, reuses
and coalesces free ranges, and implements zeroed allocation, deallocation, and
reallocation. Failed growth preserves the old allocation. Heap values survive
the return of the function that allocated them. Supported default-allocator
paths include Box, Vec growth, iterator extension, and drops. Custom global
allocators and custom allocation-error handlers are explicitly unsupported;
ordinary capacity/allocation failure stops with a trap.

Memory access selects the stack/constants or heap arena and validates the byte
range. Empty operations permit dangling pointers without dereferencing them.
The memory budget covers guest bytes and live register payloads, not total host
RSS. Checks do not establish per-allocation pointer provenance or detect every
form of Rust undefined behavior. This is a development engine for local source,
not a hostile-code sandbox or a substitute for Miri.

JIT memory instructions receive both current arena pointers on every entry.
Programs without allocation retain the smaller original emitted address-check
sequence. Scalar functions retain 16-byte frame alignment; vector and aligned
types can request stricter alignment, up to the 4096-byte frame/constant limit.
This changed the bytecode format to version 2; older artifacts require export
by the matching tool version.

Integer vector operations lower to ordinary owned scalar instructions. Covered
operations include arithmetic, masks, shifts, integer casts, comparisons,
reductions, extraction/insertion, and shuffles. Inputs are snapshotted before
output writes to preserve by-value semantics when storage aliases. The AArch64
unsigned pairwise-maximum intrinsic reached by memchr is implemented in the
same scalar IR; its LLVM-named symbol identifies the operation and does not
invoke LLVM. Native vector code emission and floating-point SIMD remain future
work.

RustCall arguments are expanded from the caller's final tuple. MIR arguments
marked for spreading map those fields into their original local slots using
rustc's layouts. This supports multi-argument closures and iterator folds,
including the closure inside Vec's trusted extension path.
