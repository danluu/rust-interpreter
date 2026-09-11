Historical snapshot before the linked-block qualification. See [README](README.md) and [current runtime work](RUNTIME-NEXT.md) for the selected implementation.

# Next runtime work, guided by existing tests

Checked add/subtract/multiply now emit their overflow results directly in the
JIT through 64 bits. Boundary/alias tests, 10,515 differential/rejection commands,
93 launcher checks, and seven production-edit workflows pass. Exact-artifact
word64 runtime fell from 2.897 to 2.609 s in five alternating pairs; the complete
edited-command median is 3.441 s, versus 1.734 s native.
[Qualified arithmetic change](results/checked-arithmetic-validation-01.json),
[seven-workflow comparison](results/e2e-checked-arithmetic-corpus-01/summary.md).

Scalar constant lowering is now qualified by 11,190 differential/rejection
commands, 93 launcher checks, and the seven-workflow corpus. Value consumers
avoid temporary storage; address consumers retain it. Valid wrapped constant
pointer relocations now preserve the target width. Word64 interpretation improved
from 17.864 to 16.953 s per edit. Paired JIT runtime measured 2.596 versus 2.547 s
with the same VM, while complete JIT commands remained approximately flat.
[Validation](results/scalar-constant-validation-01.json),
[corpus](results/e2e-scalar-constant-corpus-01/summary.md).

Checked native Div/Rem through 64 bits is now qualified. The preceding profile
executed 4.36 million divisions/remainders in the VM, and those boundaries left
another 1.18 million subtractions in short interpreted regions.
Preserve zero-divisor and signed MIN/-1 errors, aliases, error ordering, and
instruction-budget boundaries. The candidate passes its assembler oracle, bytecode suite, 11,865 differential/
rejection commands, and 93 launcher checks. Five identical-artifact pairs measured
2.571 versus 2.481 s JIT runtime, winning five of five. The word64 production edit
workflow improved from 3.472 to 3.330 s, and the full seven-workflow corpus passed.
[Division evidence](results/jit-division-validation-01.json),
[corpus](results/e2e-jit-division-corpus-01/summary.md).

MIR inlining experiments at 2×, 4×, and 8× the pinned thresholds now pass
all five word64 production edits. Five alternating runtime pairs for 8× measured
2.457 versus 1.711 s, winning all five. Calls fell from 39.14 to 17.36 million;
generated code grew from 751,644 to 799,388 bytes and peak guest memory remained
slightly below the baseline. Complete edited commands measured 2.463 s JIT,
14.094 s interpreted, and 1.641 s native. Cold JIT commands remained around seven
seconds. These flags remain explicit experiments; engine defaults are unchanged.
[All three configurations, phases, and paired evidence](results/mir-inlining-word64-01/summary.md).

The [CPU profile](results/word64-division-cpu-profile-01/summary.md) places about
31% of samples in generated code; calls, copying, the VM loop, and its JIT entry
helper account for most remaining samples. Forced host `Jit::run` inlining is now qualified. Same-bytecode runtime pairs
measured 2.458/2.274 s at default thresholds and 1.700/1.579 s at eightfold limits.
All eight production workflows, 21,927 differential/rejection commands, 93
launcher checks, and 52 bytecode tests pass. Default word64 commands measured
3.087 s JIT versus 1.601 s native; the eightfold configuration measured 2.431 s
versus 1.687 s. The latter is close to its preceding 2.463 s result because
compilation varies too. [Qualification](results/jit-entry-alwaysinline-validation-01.json).

The independent pgrust SHA-1 workflow passes both original tests, including the
million-byte reference vector and incremental updates, after five production
refactors. All modes reject the perturbed round constant. Complete command
medians are 0.781 s native, 1.255 s JIT, and 5.726 s interpreted at explicit
eightfold MIR thresholds. Five identical-bytecode pairs confirm the host-wrapper
gain here too: 0.812 versus 0.694 s. A separate operation profile records 17.96
million interpreted assertions. Word64 also executes 6.26 million assertions at
eightfold limits. Emit assertions inside JIT regions next, retaining their full
128-bit truth, original messages, failure order, and instruction budgets; then
measure both workloads. Counts alone do not establish CPU cost.
[SHA-1 workflow](results/e2e-workflow-pgrust-sha1-inline8-01/summary.md),
[runtime evidence](results/pgrust-sha1-runtime-01/summary.md).

TypeId constant lowering now preserves the compiler's numeric hash fragments
with a zero relocation base. It passes 23,277 native differential/rejection
commands and 93 launcher checks, including TypeId, Any, and error downcasts.
TypeId and Any also pass with the installed sysroot; the error fixture requires
metadata MIR. The full Nushell audit remains at 162 of 279 lowerable bodies:
the seven former TypeId blockers now reach OS or TLS blockers. No new Nushell
execution success is claimed. All nine production-edit regression workflows
pass, and the change is qualified.
[Validation](results/type-id-validation-01.json),
[post-change lowering audit](results/lowering-audit-nushell-09/summary.md),
[qualified corpus](results/e2e-type-id-corpus-01/summary.md).

The assertion JIT candidate passes 58 bytecode tests, 23,277 native differential/
rejection commands, and 93 launcher checks. Five identical-bytecode runtime pairs
improve eightfold word64 from 1.574 to 1.526 s and SHA-1 from 0.696 to 0.656 s;
default word64 is essentially flat. All recorded assertions now execute in JIT
regions, but the modest gain leaves calls, copying, and short regions as major
remaining work. All nine production regression workflows pass, but this first
candidate was rejected for its interpreter regression.
[Runtime evidence](results/jit-assertions-runtime-01/summary.md).

The initial assertion candidate is not retained as-is: three alternating
interpreter pairs confirmed regressions from 15.803 to 17.056 s for word64 and
5.326 to 5.562 s for SHA-1, losing all three pairs in both workloads. A cold
error-formatting helper also failed to restore word64 performance and was removed.
[Rejected helper](results/jit-cold-failure-comparison-01/summary.md).

Separate interpreter/JIT loop specializations are the selected follow-up.
Against the last qualified VM, interpretation improves from 16.250 to 15.336 s
for word64 and 5.271 to 4.858 s for SHA-1, winning all three pairs. JIT runtime
also improves in all five pairs for each of three configurations. Assertion
emission remains; the rejected formatter helper is absent. The VM grows by
18,208 bytes. All 58 bytecode tests, 23,277 native differential/rejection
commands, 93 launcher checks, and nine production-edit workflows pass. The change
is retained. Native still wins word64 and SHA-1; the fourteen-test Nushell group
spends about 7.25–7.46 s in Cargo and 8–10 ms executing the tests.
[Qualified production corpus](results/e2e-engine-specialization-corpus-01/summary.md).
[Selected implementation and runtime evidence](results/engine-specialization-runtime-01/summary.md).

The next candidate proves local-frame argument-copy ranges once from bytecode.
Exact trace checks cover 41.43 million of 42.24 million word64 argument copies
and 18.5236 million of 18.5240 million SHA-1 copies. The inspector measures under
0.3 ms setup and under 60 KB retained plan storage. The implementation uses safe
slice copies only when every direct-call argument is proved within the live
caller frame; other calls retain the existing checked path. All 65 bytecode tests,
40 old/new VM fixture commands, 23,277 native differential/rejection commands,
and 93 launcher checks pass. A balanced 90-command comparison selects applying
the shortcut to both engines: all six JIT pairs improve in every workload,
word64 interpretation improves slightly, and SHA-1 improves in all six pairs.
A JIT-only application regresses word64 interpretation and is rejected. All nine
production workflows now pass. The inlined word64 command rose from 2.64 to
2.98 s across corpora: its Cargo median rose from 1.09 to 1.44 s while execution
fell from 1.53 to 1.49 s. These separate runs do not isolate a causal effect.
Interleaved complete commands now verify identical executed bytecode on each edit,
using independent caches. The candidate wins 17 of 20 pairs across four workloads:
median paired gains are 6 ms for pgrust hashing, 162 ms for word64, 35 ms for
inlined word64, and 25 ms for SHA-1. Native still wins word64 and SHA-1.
[Paired complete-command evidence](results/paired-call-copy-e2e-01/summary.md).
CountOnes emission through 64 bits passed 71 bytecode tests, 23,502 native
commands, and 99 launcher checks, but was reverted. It improved the paired SHA-1
command by 14 ms while slowing default and inlined word64 by 24 ms and 38 ms.
[Rejected candidate](results/paired-popcount-e2e-01/summary.md).
The next experiment links already-compiled blocks within a function. Saved traces
identify at least 56 million word64 and 30 million SHA-1 transitions whose every
successor is compiled. The proposed native edges retain a check at every block
for the remaining virtual-instruction budget; guest calls stay in the VM.
[Proof coverage](results/call-local-copy-proof-01/summary.md),
[runtime selection](results/call-local-copy-runtime-01/summary.md).

Nushell type tests still require the metadata sysroot: the installed-sysroot
experiment stopped at missing `String::clone` MIR. Prior Cargo unit profiles show
nu-protocol compiled as a native build dependency, a guest library, and a test
target, plus downstream dev-dependency rebuilds. This is distinct from VM runtime
cost and needs a separate compilation investigation.
[Installed-sysroot finding](results/nushell-type-relations-installed-probe-01.json),
[earlier Cargo unit profile](results/cargo-profile-nushell-float-ranges-01/summary.md).

Single-thread TLS with explicit selected-test lifetimes unlocked a complete
fourteen-test Nushell type family. The implementation passed
9,840 differential/rejection commands and 93 launcher checks: mutable TLS initializer ranges reset between tests,
ordinary statics stay shared, and TLS destructor registration remains rejected.
RandomState runs its ordinary Rust body with a checked macOS entropy primitive.
Concrete enum layouts also identify impossible variant branches after strict
checking; these no longer expand unsupported calls in unreachable MIR blocks.
The complete fourteen-test type family passed five production edits: 9.600 s
native, 5.120 s interpreted, and 5.303 s JIT median commands. Guest execution is
about 8–10 ms; Cargo dominates. Cold commands were 68.034/64.659/63.773 s, excluding
the 10.997 s reusable MIR setup. The [six-workflow corpus](results/e2e-tls-corpus-01/summary.md)
also passed on this tool build. Word64 remains 3.735 s JIT versus 1.703 s native.
[Type-relation workflow](results/e2e-workflow-nushell-type-relations-01/summary.md),
[TLS validation](results/single-thread-tls-validation-01.json).

Non-capturing closure function pointers and consistent zero-sized call arguments
are implemented and qualified by 8,116 differential/rejection commands, 93 launcher
checks, and the [six-workflow call-ABI corpus](results/e2e-call-abi-corpus-01/summary.md).
That corpus includes real production edits and unchanged existing tests. The
fourteen-test type group was still blocked at RandomState TLS in that build.

Structural smart-pointer unsizing now follows compiler field layouts and
preserves allocator state. It passes 6,766 native differential/rejection commands
and 93 launcher checks. The complete Nushell audit grew from 87 to 90 lowerable
bodies with no regressions. Three subtype tests gained support, but the full
family subsequently passed closure pointer lowering and reached TLS. TLS and OS calls
remain separate limitations. [Coercion validation](results/structural-coercion-validation-01.json),
[complete audit](results/lowering-audit-nushell-07/summary.md).

The previous runtime optimization inlined the checked JIT transition helper. It reduced
paired word64 runtime from 3.033 to 2.887 s and complete edited commands from
3.908 to 3.705 s, versus 1.703 s native. All six production workflows across
five projects passed on one frozen build. Two copy optimizations failed paired
comparisons and were removed. [Current corpus](results/e2e-jit-entry-inline-corpus-01/summary.md),
[profile and rejected experiments](results/word64-cpu-profile-02/summary.md).

Expanded compatibility originally exposed the runtime-heavy fre workflow.
The mutable-static and `#[track_caller]` support increased the
independently lowerable fre test bodies from 79 to 127 of 389; this audit does
not establish test success. All 12 existing word64 matcher tests have now been
measured with production edits and unchanged exhaustive inputs. [Completed measurements](results/e2e-workflow-fre-word64-01/summary.md)
show medians of 13.164 s with the JIT, 27.465 s interpreted, and 1.707 s natively. Native
execution takes about 0.21 s; the guest executes 5.18 billion operations. This
makes runtime optimization the next investigation, starting with MIR
optimization and measured call/storage overhead.

The [six-test fre algorithm workflow](results/e2e-workflow-fre-class-sequence-01/summary.md)
remains a contrasting compile-dominated case: 0.74–0.75 s versus 1.32 s natively,
with about 5 ms guest execution. Both kinds of workload belong in subsequent
regression comparisons. The [3,500-body survey](results/lowering-audits-01.md)
also keeps TLS and nested dynamically sized layouts visible as compatibility
limitations. Result test adapters and mutable statics are now implemented;
thread-local state needs explicit test-lifecycle semantics before support.

The [runtime profile](results/word64-runtime-profile-01/summary.md) found
126.6 million guest calls with default MIR and 39.0 million with MIR inlining.
A [reusable register stack](results/register-stack-01/summary.md) now eliminates
per-call register allocation/free while preserving zero initialization and the
live-memory budget. Native differential and boundary checks pass. On unchanged
recorded artifacts, JIT execution medians dropped from 12.619 to 9.746 s and
from 6.014 to 4.841 s respectively. These are runtime diagnostics. The completed
[production-edit comparison with MIR level 3](results/e2e-workflow-fre-word64-mir3-arena-01/summary.md)
measured 5.731 s JIT, 18.017 s interpreted, and 2.081 s native. The JIT is much
faster than the previous build but still loses this longer workflow to native.

The JIT now implements constant/local-address propagation inside compiled
straight-line regions, with dynamic checks retained for unknown pointers.
The new loop-backedge regression exposed and fixed a deferred-spill error;
bytecode, native differential, and launcher validation pass. The full word64
workflow now measures 4.660 s JIT versus 1.644 s native, preserving all original
exhaustive tests. [Latest complete-command comparison](results/e2e-workflow-fre-word64-jit-facts-01/summary.md).
All six workflows across five projects passed the
[frozen-build regression run](results/e2e-jit-facts-corpus-01/summary.md).

The [CPU profile](results/word64-cpu-profile-01/summary.md) places about a
quarter of samples in generated code, with substantial VM-loop, copying,
register-resize, and transition costs. Possible
bounded changes include absorbing Jump/Switch into emitted region exits, and
reducing temporary register storage. Do not infer runtime wins from operation
counts alone. Resetting exporter register numbers across MIR statements would
invalidate the JIT's current function-wide dead-overflow/liveness assumptions;
that requires an explicit correctness design before implementation. The integer overflow/logarithm panic helpers now let the full word64 group use
the installed sysroot. Its [production-edit comparison](results/e2e-workflow-fre-word64-installed-01/summary.md)
measures 4.736 s JIT versus 1.643 s native, without extra MIR setup.

The first control-flow change removes jumps to the following retained
instruction, remapping every branch target in one linear pass. Unit and native
differential tests pass, including chains, branch joins, invalid targets, and
loop backedges. The [production workflow](results/e2e-workflow-fre-word64-fallthrough-01/summary.md)
measured 4.574 s JIT. Removing exported operations changes artifact instruction
counts; the VM still counts exactly the instructions it executes.

The JIT now absorbs unconditional jumps and switches of up to 16 cases into
region exits. Emitted code returns a checked successor index, preserving full
128-bit first-match semantics and virtual instruction budgets. The paired
runtime median changed only from 3.671 to 3.642 s; complete edited commands
changed from 4.574 to 4.538 s. This is a small gain, with shared-host variation.
[Validation and comparison](results/jit-branches-validation-01.json).

Register backing storage now retains initialized elements after a call returns.
A conservative proof allows skipping repeated clearing only when each register
read follows a write in the same basic block. Other functions keep full
initial-zero behavior. All bytecode tests, native differential checks, and 93
launcher checks pass. Paired word64 runtime medians changed from 3.734 to
3.147 s with identical artifacts and instruction counts. The six-workflow
[production corpus passed](results/e2e-register-init-corpus-01/summary.md).
Word64 edited commands changed from 4.538 to 3.908 s, versus 1.674 s native.
The other five workflows remain faster than native in this comparison.
[Register initialization validation](results/register-init-validation-01.json).

The latest compatibility change implements nested dynamically sized layout:
`ArcInner<dyn Error>`, `ArcInner<str>`, and `Path`. The previous Nushell audit
recorded 133, one, and 11 first blockers in these areas respectively. Match the
pinned compiler's size, alignment, field projection, and nested unsizing rules;
correcting size queries alone would leave misaligned trait-object fields.
Native differential checks now pass, including nested alignment, packing,
upcasts, and destruction. The latest Nushell audit lowers 87 of 279 bodies;
39 new bodies previously stopped at the nested Arc layout, and one at the
earlier caller-location limitation. [Audit](results/lowering-audit-nushell-06/summary.md).

The full ten-test last-result group was selected with unchanged 100-item,
50-row, and 10,000-byte inputs. Supporting ordinary Rust intrinsic bodies
resolved multiply-with-carry, and explicit pointer-mask lowering resolved the
next blocker. Both pass native differential checks, but the complete group
still requires `std::thread::current::CURRENT` TLS. Keep it recorded as blocked;
no custom runtime or edited-command timings are qualified for that group.
[Blocked attempt](results/nushell-last-result-blocked-01.json).

The completed production comparison uses all eight existing span tests, including
the 20,000-byte interruption input. These became independently lowerable with
nested layout support. Its five refactors preserve polling at 16,384-byte
intervals and test source; the negative control delays the poll past the
original input length and must fail the existing interruption test.
The workflow is `--project nushell --workflow span-signals --batch --std-mir`.
Edited-command medians were 5.260 s JIT, 6.047 s interpreted, and 8.999 s native.
Guest execution took only 14–24 ms; Cargo accounts for nearly all command time
and most of the difference between custom modes. The extra metadata sysroot
setup is excluded from those times and makes this group's first custom use
slower than native. [Complete comparison](results/e2e-workflow-nushell-span-signals-01/summary.md),
[phase medians](results/span-signals-stages-01.json).

The engine now runs selected existing tests in pgrust, fre, Nushell, Ruff, and
private rg-aot.
Full edited-test commands show useful compile-time savings, but these do not
qualify whole applications or suites. The heap/SIMD build has been measured on
all five projects, including successful first builds in independent empty
artifact caches. See [the common-build comparison](results/e2e-tests-heap-corpus.md).

The rg-aot existing line-iteration test now passes in both engines. It uses
heap-backed collections without the filesystem setup needed by its broader
integration tests. Keep private source and detailed logs under `.work`; report
only aggregate outcomes outside it.

## Implemented: guest heap and collection prerequisites

These mechanisms are implemented and pass the local differential suite and the
selected rg-aot test. This does not establish complete collection or application
support.

* Keep the existing constant/stack arena and use a separate heap arena with
  tagged guest offsets. Reserve a tag distinct from function handles. Guest
  addresses remain offsets; no guest address becomes a host pointer directly.
* Implement allocation, zeroed allocation, deallocation, and reallocation in
  our runtime. Track sizes and alignments, reuse/coalesce free ranges, preserve
  old allocations on failed reallocation, and enforce the combined guest-byte
  and live-register budget. Reject malformed allocator calls. Do not silently
  bypass a project's custom global allocator or allocation-error handler.
* Lower sized `size_of_val`/`align_of_val` from rustc layout information, then
  support slice metadata where required by actual tests. Keep unsupported trait
  object layouts explicit.
* Extend checked JIT memory access to select the current stack or heap storage.
  Preserve the existing emitted path when the exported program cannot allocate,
  avoiding an unconditional penalty to pgrust's long scalar test. Generated
  blocks retain no pointers across calls, allocation, or arena growth.
* Correct zero-length memory operations to permit Rust's valid dangling empty
  pointers without dereferencing them. Validate nonzero ranges before access.

Validation exercises allocations surviving guest returns, moving values
between stack and heap, 64-byte alignment, zeroed reused storage, growth/shrink,
reallocation failure, drop effects, and memory limits. Heap and integer SIMD
fixtures each compare 111 inputs against native Rust in both engines. RustCall
tuple expansion supports the closure calls used by iterator folds and
`Vec::extend`. SIMD currently lowers to our scalar operations, including the
AArch64 unsigned pairwise-maximum intrinsic reached by memchr. No LLVM is used
to implement these guest operations.

Compare the existing rg-aot test with native Cargo, then measure production
and test edits through complete commands. Do not disable its SIMD paths to
obtain a favorable result.

## Other priorities

The heap build exposed a pgrust interpretation regression. Inlining the memory
range/read helpers reduced execution from roughly 0.435 s to 0.396 s; full edited
commands moved from 0.912 s to 0.870 s. The JIT full command measured 0.615 s after
the change, with native at 0.667 s in that run. Keep the simple helper change;
further runtime complexity needs a larger demonstrated benefit.
[Follow-up measurement](results/e2e-tests-pgrust-memory-inline-02/summary.md).

The prebuilt standard library omitted `StrSearcher::new`, blocking Nushell's
four-test keyword group. The opt-in `--std-mir` path now checks a task-owned
copy of the standard-library workspace and publishes reusable metadata. It
leaves installed toolchain files untouched. Cargo's `-Zbuild-std` uses native
build units even for `cargo check`, so this path invokes a direct metadata-only
check instead. No native guest execution fallback is used.

Function-pointer support is conservative: an indirect call requests every
address-taken body with a compatible argument/result byte layout; unknown
layouts are retained. The runtime enforces the same call-layout checks. This
can omit unused formatting callbacks without omitting possible valid calls.
Virtual calls now reuse these guest handles; broader closure coercions and
unsized pointer carriers still need coverage.
Ordinary Rust checking remains the default.

The production-edit benchmark now demonstrates that batching selected tests
matters more than another small scalar runtime optimization for this workflow.
Three serial custom commands took about 2.1 s per edit; batch selection reduced
that to about 0.72 s, versus 1.31 s natively. The next comparison varies the test
selection after each edit. The original separate-per-selection cache then took
roughly 4.2 s, versus 1.31 s natively. A shared target with explicitly tracked
entry-selection inputs passes launcher checks and reduced the workflow to
0.72–0.73 s, versus 1.29 s natively.

The benchmark is `scripts/bench_e2e_workflow.py`: five cumulative production
refactors in fre's integer codec, followed by its three existing boundary/error
tests. Test source is unchanged. A deliberately wrong production encoding must
first fail. `--batch` selects one custom invocation; `--vary-selection` chooses
the tests relevant to each edit. Array equality in the error-path test required
lowering `raw_eq` to checked byte comparison. Repeat this broader workflow on
other projects, then use the observed compilation/execution split to choose
between deeper runtime work, a persistent frontend, and further artifact reuse.

Pgrust's complete four-test hashfn library suite now passes five production
refactors: JIT 0.602 s, interpretation 0.837 s, native 0.649 s. Reaching the
array-construction test required preserving impossible uninhabited-discriminant
branches as traps. Saturating integer arithmetic now supports Vec's collection
path and passes the boundary/random differential suite.

Nushell's four-test group now passes five production refactors with changing
selections: JIT 0.420 s, interpretation 0.431 s, native 0.640 s. Shared metadata
installation took 10.997 s, including 9.185 s of compilation. That setup is
separate from cold workspace commands and makes total first use slower than
native in this run; keep the option explicit. The launcher now passes 48
checks, including native host build scripts and procedural macros with target
MIR dependencies. [Measurements](results/e2e-workflow-nushell-std-mir-01/summary.md).

Ruff's six-test registry group now passes with formatting, virtual calls,
immutable statics, typed swaps, and unpredictable selections. The differential
fixture compares trait upcasts, aggregate arguments/results, boxed dynamic
layout and destruction, slice destruction, and cyclic static references
against native Rust on 111 inputs per engine. Long straight-line initializers
required bounding JIT regions to keep memory-check branches in range; tests
cover large code mappings, faults, and instruction budgets across those regions.

Five Ruff production refactors measured 2.982 s with the JIT, 3.002 s interpreted,
and 5.449 s natively. The small whole-command difference between custom modes
is within host/compilation variation, despite a useful runtime reduction on
the complete batch. Frontend work takes over two seconds per edited command;
profile its passes before investing in more runtime optimization.
[Measurements](results/e2e-workflow-ruff-registry-02/summary.md).

The private rg-aot production workflow also passes five refactors, retaining
its existing test and SIMD paths: JIT 0.182 s, interpretation 0.184 s, native
0.552 s. Its adapter and detailed records remain under `.work`.
[Aggregate report](results/e2e-workflow-rg-aot-production-01/summary.md).

## Frontend direction

The [Ruff pass profile](results/frontend-profile-ruff-01/summary.md) covers three
real production edits followed by the same six-test batch. Median macro
expansion time is 1.008 s, type checking 0.223 s, and borrow checking 0.066 s.
These are nested instrumented timings, not additive phase totals. Ordinary
borrow checking therefore accounts for little of this workflow's remaining
latency.

The pinned compiler already defaults to same-thread procedural macro execution.
Its experimental derive cache is disabled: the [compiler documentation](https://doc.rust-lang.org/nightly/unstable-book/compiler-flags/cache-proc-macros.html)
states that macros reading external state can produce stale expansions with
that flag. A general-purpose engine needs a sound input contract before using
such a cache.

The measured alternative optimizes host build tools. Cargo normally
[builds procedural macros, build scripts, and their dependencies without optimization](https://doc.rust-lang.org/cargo/reference/profiles.html#build-dependencies).
Level 1 reduced Ruff's macro-expansion phase to 0.756 s, close to level 3's
0.732 s, with a smaller cold cost. In the complete workflow, level 1 measured
2.574 s JIT, 2.592 s interpreted, and 5.071 s natively. The approximately 20 s
extra first-build cost needs roughly 50 edits to amortize in this comparison.
Retain project defaults and document this as an optional setting. All modes
used the same host settings; guest execution remains in the custom engines.
[Complete-command measurements](results/e2e-workflow-ruff-hostopt1-01/summary.md).

The next compatibility probe selects Nushell's seven existing floating-point
range tests unchanged. Use their actual failures to guide support for numeric
operations and any required runtime primitives, then measure production edits
with those tests. Keep arithmetic comparisons against native Rust separate
from whole-command performance measurements.

That probe now passes. It required scalar `f32`/`f64` operations and conversions,
then the atomics used by `Arc` destruction. Floating operations remain interpreted
in both modes; the JIT handles surrounding supported instructions. Atomic
operations lower to checked sequential operations under the engine's one-thread,
exclusively owned guest-memory contract. This does not add guest threads,
external shared memory, mutable statics, or an OS signal bridge.

Floating and atomic fixtures each match native Rust for 111 inputs in both
engines. The checks include floating saturation and double-rounding boundaries,
all available ordinary integer atomic widths/orderings, pointer exchange, weak
reference upgrades, and destructor counts. Invalid atomic alignment, bounds,
read-only writes, and orderings are rejected. The bytecode suite and all 59
launcher checks pass. [Recorded qualification](results/numeric-runtime-validation-01.json).

The production comparison uses `--project nushell --workflow float-ranges
--batch --std-mir`. Its five cumulative refactors preserve the seven tests byte
for byte. It first doubles the iteration step and requires actual test failures
in every engine. Preserve the older parser-keyword workflow as the default so
its existing benchmark command keeps identifying the same workload.

The completed range workflow measured 5.087 s JIT, 5.173 s interpreted, and
7.438 s natively. Cold times were close before standard-library MIR setup;
including it makes custom first use slower. VM execution accounts for only
3–4 ms of the approximately five-second custom edit command. The selected
frontend uses about 1.08 s; other invalidated Nushell crates account for much
of the rest. The next diagnostic records Cargo unit timelines across actual
edits, rather than adding floating-point JIT instructions with little potential
effect on this workload. [Measurement](results/e2e-workflow-nushell-float-ranges-01/summary.md).

The pgrust regression comparison remains 0.620 s JIT, 0.871 s interpreter,
0.655 s native. Preserve the native tier for long compute tests. Broader
compatibility work should also measure which existing test groups remain
blocked, to avoid choosing future work only from already-supported routines.

The [Cargo profile](results/cargo-profile-nushell-float-ranges-01/summary.md)
records 19 rebuilt units per range edit. Median durations include native
`nu-protocol` for a host build script (1.35 s), its test metadata (1.12 s), its
ordinary metadata (1.05 s), and `nu-command` checking (0.81 s); these overlap.
`nu-cmd-extra` uses `nu-protocol` as a build dependency while generating HTML
theme data. Retain that native host behavior. First check whether this numeric
workflow actually requires the optional standard-library MIR sysroot: avoiding
an unnecessary sysroot could reduce setup and host/target separation costs
without changing guest semantics or project code.

The installed-sysroot probe and complete range workflow both pass. Prefer it
for this group: 3.946 s JIT, 3.954 s interpreted, 6.413 s native after five real
edits; cold commands are 56.548/54.402/66.528 s without separate MIR setup.
Native warm times also changed between runs, so do not ascribe the whole
cross-run difference to the sysroot. The full float fixture passes another
111 native comparisons per engine with the installed sysroot. The broader
atomic fixture still needs the missing `alloc::sync::panic_arc_overflow` MIR;
the range graph only needs a smaller set of Arc operations.
[Default-sysroot measurement](results/e2e-workflow-nushell-float-default-sysroot-01/summary.md).

Next, broaden the compatibility evidence: discover existing test names and
measure which bodies can be lowered after ordinary checking, grouping failures
by the missing operation. Treat this as lowering coverage, not a claim that
the tests run or that custom harness semantics are supported. Use those counts
to choose the next runtime capability. A separate performance question is how
much eager MIR retention for unused dependency bodies costs; investigate it
only while retaining strict checks and explicit failure for missing runtime
MIR. No reduced-retention policy has been implemented or measured yet.
