# Rust development engine experiments

A custom Rust bytecode interpreter and direct AArch64 JIT, using rustc for ordinary
frontend checking and MIR. The engine runs selected existing library tests in
pgrust, fre, Nushell, Ruff, and private rg-aot. Whole applications, arbitrary
OS/FFI calls, guest threads, and native unwinding remain unsupported.

The retained experimental JIT forwards scalar loads from values already available
for the same proven local-frame bytes. Across nine real source-edit/build/test
workflows it improves **25/45 complete commands** against the preceding engine
and **30/45 against native Cargo**. The compute workflows save paired medians of
**279 ms on token-phrase, 56 ms on folded trie, 30 ms on SHA-1 and 7 ms on TLS**.
Ruff regresses 42 ms and larger Nushell 33 ms. Folded's marginal command median
regresses 148 ms despite its lower paired median. Native remains much faster on
token and folded; this does not establish a general warm-compilation gain.
[Complete results, including cold costs](results/local-memory-forwarding-01/summary.md).

All **183 bytecode tests**, **11 exporter tests**, **47,004 native differential
commands** and **245 TLS/callback checks** pass. All **382 active fre tests** pass
against fresh native executions; seven remain ignored. All 63 new workflow
artifacts and every fre artifact match the preceding build. Independent builds
reproduce the measured binaries exactly. A final correction to a new test's
expected result also reproduces those binaries; it changes the source key to
`57a54edd` from measured `af9aa691`. Original tests, strict frontend checking,
writes, destination checks, final register spills and instruction budgets remain
intact. [Qualification](results/local-memory-forwarding-01/qualification.json),
[next work](RUNTIME-NEXT.md).

The preceding experimental build combines restricted MIR scalar promotion with
the custom native register cache. Across nine real source-edit/build/test
workflows it wins **30/45 complete commands** against its parent and **33/45
against native Cargo**. The four compute workflows save paired medians of
**78 ms on folded trie, 175 ms on token-phrase, 98 ms on TLS and 47 ms on SHA-1**.
Native remains much faster on token-phrase and folded trie. Larger Nushell
regresses **558 ms**, almost entirely in Cargo; Ruff and private rg-aot have
smaller regressions. Several cold samples are slower. These results do not
establish a general warm-compilation improvement.
[All samples, stages and cold costs](results/scalar-packed-cache-01/summary.md).

All **172 bytecode tests**, **11 exporter tests**, **47,004 native differential
commands**, and **245 TLS/callback checks** pass. Fresh exports preserve all
**382 active fre tests** against fresh native controls; seven remain ignored.
Every candidate artifact in the nine workflows matches the earlier scalar
implementation, and both combined binaries reproduce exactly from a fresh
source copy. Ordinary Rust type and borrow checking, original assertions and
wrong-edit controls remain intact. The explicit fre allocation limit is
150,000; the default remains 100,000. [Next work and limitations](RUNTIME-NEXT.md).

The preceding build keeps two values with known-zero upper halves in native
registers, or one full-width value. Across four actual source-edit workflows it
improves **15/20 complete commands** and **20/20 execution stages** against its
parent. Paired command savings are **222 ms for token-phrase**, **59 ms for folded
trie**, and **22 ms for TLS**; SHA-1 is flat overall. Native Cargo still wins
15/20 comparisons and remains much faster on token-phrase and folded trie.
[Complete results and cold timings](results/packed-native-cache-01/summary.md).

All **169 bytecode tests**, **47,004 native differential commands**, and **245 TLS
checks** pass. All **382 non-ignored fre tests** pass against fresh native
executions at the explicit 150,000 allocation limit; seven remain ignored. An
additional 70 retained project commands preserve original outcomes, including
wrong-edit rejections. Their historical native controls are separate from the
fresh edit benchmarks. Both measured binaries reproduce exactly. The exporter,
strict frontend checks, bytecode, and default allocation limit are unchanged.
This remains a targeted runtime gain, without a broad warm-compilation claim.

The preceding build emits byte comparisons directly in the custom AArch64 JIT.
On the exhaustive token-phrase edit workflow it wins all five commands against
its parent, saving a paired **301 ms**, including **244 ms in execution**. Native
Cargo remains much faster: medians **2.264 s native / 7.649 s parent / 7.378 s JIT**.
The other three workflows have essentially flat execution. Folded-trie regresses
19 ms per command; TLS command savings are mainly Cargo. The initial TLS runtime
screen's 2.8 ms regression remains recorded. This is a targeted experimental gain,
with **14/20** command wins against the parent and **6/20** against native.
[Complete comparison and cold timings](results/native-compare-bytes-01/summary.md).

All **165 bytecode tests**, **47,004 native differential commands**, and **245 TLS
checks** pass. All **382 non-ignored fre bodies** pass at the explicit 150,000
allocation limit, against 382 fresh native controls; seven remain ignored. An
additional 70 retained-program commands across pgrust, Nushell, Ruff and private
rg-aot preserve all original outcomes and wrong-edit rejections. That additional
replay is behavior coverage using historical native controls, not fresh build-time
evidence. Every artifact pair in the four real edit workflows is identical, and
all five source pins are restored. The exporter binary and strict frontend are
unchanged. [Current plan and limits](RUNTIME-NEXT.md).

The preceding build adds an explicit live-allocation budget to the VM and launcher:
`--allocation-limit 150000`. The default remains 100,000; the maximum is one
million. Guest bytes have a separate budget. This lets all **382 non-ignored fre
tests pass** with the explicit limit, against 382 fresh native controls. Seven
tests remain ignored. All **161 bytecode tests**, **47,004 native differential
commands**, and **245 TLS checks** pass. Fresh builds reproduce the measured tools.

This is a capability gain with a measured cost. The new exhaustive token-phrase
edit loop takes **7.315 s with the JIT versus 2.037 s native**, losing all five
edited-command comparisons. At the default limit, folded-trie saves a paired
31 ms per command, while the pgrust interpreter control regresses 10 ms. Two
layout alternatives failed to remove that regression. The native-comparison follow-up above targets
the 8.4 million interpreted byte comparisons in that profile.
[Allocation-budget results](results/allocation-budget-01/summary.md),
[current plan](RUNTIME-NEXT.md).

The preceding retained experimental build keeps one dynamic 128-bit value in native registers
inside each compiled region. It reduces traffic through the VM register array,
preserving the exact guest bytecode and execution accounting. The exporter and its
strict type and borrow checking are unchanged.

It passes **151 bytecode tests**, **47,004 native differential commands**, and
**245 TLS checks**. Replaying all 389 retained fre bodies preserves **381 passes**,
one identical allocation-capacity error, and seven ignored tests, with 382 fresh
passing native controls. The 54 bodies with random-input-dependent count variation
also match exactly in **108 controlled-input trace pairs**. A fresh build reproduces
both measured tool binaries.

Across eight real production-edit workflows in all five projects, it wins **29/40**
commands against its parent and **29/40** against native Cargo. All fifteen folded
trie, TLS and SHA-1 edited commands improve against the parent, saving paired
medians of **157, 67 and 99 ms**. Native still wins every folded-trie and SHA-1 pair.
Short Nushell and Ruff regress by 8 and 30 ms. Larger Nushell improves by 740 ms,
almost entirely in Cargo; that does not establish a gain caused by the register
cache. These small samples do not establish a broad warm-build improvement.
All 56 artifact pairs are exact, every wrong edit is rejected, and all five source
pins are restored. [Complete results and cold timings](results/native-register-cache-01/summary.md).

The preceding scalar-frame change remains integrated. It shares storage only for
disjoint primitive values, reducing the traced declared direct-call frame volume
by about 8%. Arguments/results, aggregates, exposed addresses, call destinations
and entry-live values stay dedicated; initialization is preserved.
[Scalar-frame results](results/scalar-frame-dense-01/summary.md).

Earlier native controls also included the target MIR settings used by the JIT.
The then-current JIT lost all ten folded-trie/SHA-1 edited commands to both native
configurations; matching-MIR native won eight of ten against standard native.
[Native control results](results/native-mir-controls-01/summary.md).

The direct-call-return shortcut passed focused correctness checks but won only
6/15 edited commands. It remains archived without integration.
[Rejected experiment](results/native-call-exit-01/summary.md).
The allocation-budget follow-up above resolves that count limit when explicitly requested.

The preceding CFG build remains archived. Its larger Nushell cold run regressed
from 72 to 106 seconds; the current 64-second sample does not explain that earlier
regression. [Previous CFG results](results/cfg-single-copy-01/summary.md),
[initial scalar prototype](results/scalar-frame-probe-01/summary.md).

The preceding call-order build runs forwarding elimination before leaf inlining,
so expansion cannot hide small forwarding wrappers. It preserves all **381 fre
passes** with freshly exported bytecode and 382 passing native controls; one test
has the same allocation-capacity error, and seven are ignored. All 138 bytecode
tests, 47,004 native differential commands and 245 TLS checks pass.

Across eight production-edit workflows in all five projects, it wins **22/40**
commands against its parent and **30/40** against native Rust. Folded trie saves a
paired **62 ms** per command, including 36 ms in execution. Larger Nushell regresses
by a paired **261 ms**, mostly in Cargo; execution is effectively flat. Native
still wins all ten folded-trie/SHA-1 comparisons. Retain this as an experimental
runtime improvement without a broad warm-build claim. All 56 artifact pairs are
audited, and all baseline artifacts match the preceding retained run.
[Complete results and limits](results/inline-order-01/summary.md).

The following measurements describe earlier retained experiments.

The preceding native 128-bit subtraction/comparison candidate preserves **381 ordinary
fre test passes** in retained-program replay, with 382 fresh native controls. One
test retains the existing allocation-count failure; seven are ignored. All 134
bytecode tests, 47,004 native differential commands, and 245 TLS checks pass.

On the tuned folded-trie workflow, it wins four of five complete production-edit
commands against its parent, saving a paired median of **95 ms**, including 54 ms
in execution. The TLS workflow is effectively flat (+3.4 ms paired). All 14 artifact
pairs are identical, and every wrong edit is rejected. Across eight workflows in
all five projects, it wins **20/40** commands against its parent and **30/40** against
native. Ruff regresses by a paired 108 ms and larger Nushell by 302 ms, mainly in
Cargo; the exporter binaries are identical. Native wins all ten folded-trie/SHA-1
comparisons. Retain this as a targeted runtime improvement, without a broad
build-time claim. All 56 artifact pairs in the complete comparison are identical.
[Candidate results and limits](results/native-wide-integers-01/summary.md).

The preceding cached-readiness change improved all ten execution-stage pairs but
only five of ten complete edited commands. The native-code cap remains 16 MiB;
strict frontend and complete bytecode checking remain enabled.
[Parent comparison](results/lazy-cached-guard-01/summary.md).

With that same engine, increasing rustc's MIR inlining budget improves all five
folded-trie production-edit commands: a paired median saving of **428 ms**, including
369 ms in execution. It still loses to native in all five comparisons: medians are
**3.077 s JIT versus 1.883 s native**. These are edits to production code followed
by the 18 unchanged original tests. MIR defaults remain unchanged.
[Complete MIR comparison](results/paired-folded-mir-inline8-01/summary.md).

The earlier forwarding experiment bypassed functions that only pass their arguments
to another function. It preserves function IDs and layouts, and adds no bytecode or
native-code size in the audited programs. All **125 bytecode tests**, broad native
checks, and the fresh **320 passed / 62 lowering blocked / 7 ignored** fre survey pass.

Across thirteen production-edit workflows, it wins **37/65** commands against the
prior JIT and **42/65** against native Rust. The TLS-heavy workload saves a paired
median of 204 ms per command; folded-trie saves 51 ms. Ruff regresses by 98 ms and
larger Nushell by 264 ms, mainly in Cargo. All 91 artifact pairs pass an exact
check that only direct-call targets changed. Keep this as an experimental runtime
improvement; the results do not establish a broad build-time improvement.
[Complete comparison and decision](results/paired-direct-forwarding-corpus-01/summary.md).
[Current coverage](results/audit-execution-fre-direct-forwarding-01/summary.md).

The preceding capability experiment adds checked guest C/System allocation and TLS
cleanup. All 17 previously blocked TLS-dependent fre tests now pass against fresh
native controls: **320 passed, 62 lowering blocked, 7 ignored**. All 119 bytecode
tests pass. Running standard TLS cleanup currently requires `--trap-unsupported-calls
--run-try-callbacks`; the latter executes normal-return try callbacks while actual
panics and unwinding still fail. The five-edit comparison on those unchanged
tests takes 2.42 s with the JIT versus 1.88 s native in the medians; the JIT loses
four of five warm comparisons. Call overhead is the next measured target.
[Capability and benchmark](results/guest-tls-capability-01/summary.md).
[Fresh coverage](results/audit-execution-fre-guest-tls-01/summary.md).

The preceding dispatch experiment avoids repeating its loop after native code exits.
All 107 bytecode tests and broad native checks pass. It improves all **20/20
complete production-edit commands** in four compute workflows, with paired median
savings of 94 ms for folded-trie, 68 ms for word64, 58 ms for inlined word64,
and 9 ms for SHA-1. Execution stages also improve in all twenty pairs. Both actual
tool binaries differ, but all executed bytecode pairs are identical. An independent
runtime screen improves 23/24 pairs with identical guest work and complete profiles.
Native Rust still wins 18/20 compute comparisons. Fresh native controls preserve
all 303 passing fre tests and all 389 classifications. The complete twelve-workflow
corpus wins 39/60 commands against the prior JIT and 42/60 against native. Ruff and
larger Nushell regress by paired medians of 180 ms and 383 ms, almost entirely in
Cargo. This remains an experimental baseline, without a broad build-time speed claim.
[Full dispatch corpus and decision](results/paired-native-exit-dispatch-corpus-01/summary.md).
[Dispatch edited-command comparison](results/paired-native-exit-dispatch-compute-01/summary.md).
[Dispatch runtime screen](results/native-exit-dispatch-real-screen-01/summary.md).

The retained population-count experiment adds native counts through 64 bits. Its 104
bytecode tests and broad native differentials pass; the exporter and compared
bytecode are unchanged. A runtime screen improves 19/24 pairs, including a 21 ms
SHA-1 saving, but folded-trie regresses by 27 ms. The four real production-edit
workflows then win 14/20 commands. SHA-1 improves all five, saving 27 ms per command
and 19 ms in execution by paired medians. Word64 command gains are mostly Cargo;
folded-trie is effectively flat. Fresh native controls preserve all 303 passing fre tests and all 389 prior
classifications. The complete twelve-workflow corpus wins 37/60 comparisons against
the prior JIT and 44/60 against native. Many command gains occur outside execution;
Ruff retains a 12 ms paired regression, and larger Nushell varies by seconds.
This remains experimental, without a broad opcode-driven speed claim. The measurements below retain earlier
experiments and their limitations.
[Population-count full corpus](results/paired-native-popcount-corpus-01/summary.md).
[Fresh fre coverage](results/audit-execution-fre-native-popcount-01/summary.md).

The earlier CPU-query candidate passes **303 original fre tests**, adding 61
against fresh native controls. It executes actual read-only macOS feature/family
queries through a checked runtime primitive. Its complete 18-test folded-trie
workflow still loses to native after production edits: **3.941 s JIT versus
1.768 s native**, with interpretation at 21.619 s. It wins 21/55 paired edited
commands in the initial corpus. A diagnostic Nushell repeat still loses three of
five pairs; Cargo reports locate most variation before the selected test target.
The CPU-query build remains an experimental baseline, not the selected build.
[Candidate coverage and measured limits](results/cpu-feature-capability-01/summary.md).
[Nushell diagnostic](results/cpu-feature-nushell-diagnostic-01/summary.md).

The retained experimental baseline extends native copies from 32 to 128 bytes,
targeting 18.9 million interpreted copies in the complete folded-trie workflow. All 96 bytecode
tests and broad native differentials pass. The real-artifact screen improves
folded-trie and word64, with a small SHA-1 regression without leaf inlining.
It wins **38/60 complete production-edit pairs across twelve workflows**. The
folded-trie and two word64 configurations win all fifteen pairs; SHA-1 and the
frontend-heavy workflows remain mixed. Native wins all twenty compute comparisons,
while the candidate wins the other forty native comparisons. The larger Nushell
command regresses by 659 ms in the median paired comparison, mostly in Cargo;
both compared exporters are identical. Fresh controls preserve all 303 passing
original fre tests. This remains an experimental baseline, not a universal win
or whole-application support.

Compiler scratch-frame reuse was subsequently tested and set aside: it won
19/24 runtime pairs but only 10/20 complete edited-command pairs, losing all five
inlined-word64 pairs. The copy-emitter source and binaries were restored.
[Scratch-reuse decision](results/paired-temporary-frame-compute-01/summary.md).
Extending leaf-inlining eligibility to 128-byte aggregates subsequently won 12/20
edited-command pairs but regressed the complete folded-trie workflow in 4/5 pairs.
All five SHA-1 pairs used identical bytecode. That variant remains unqualified.
[Unguarded comparison](results/paired-native-medium-leaf-compute-01/summary.md).

A general frame-growth guard subsequently reverses the folded-trie regression:
4/5 edited commands improve, with a 25 ms median paired saving. Word64 saves 36 ms
and inlined word64 saves 9 ms. The changed-bytecode cases win 10/15 pairs; native
still wins 17/20 overall comparisons. All 303 original fre passes survive fresh
native controls. The complete twelve-workflow corpus wins **35/60** pairs,
including 30/47 changed-bytecode pairs. Ruff and larger Nushell regress by 145 ms
and 556 ms in the median paired command comparison, mostly in Cargo. This does
not establish a broad speed improvement; leaf inlining remains opt-in.
[Guarded corpus](results/paired-native-medium-leaf-frame-guard-corpus-01/summary.md),
[fresh coverage](results/audit-execution-fre-native-medium-leaf-frame-guard-01/summary.md).

A control now compares byte-for-byte identical exporters and VMs on fifteen real
production edits. Nominal median command gains are 10 ms for fre, 17 ms for Ruff,
and 724 ms for larger Nushell; individual Nushell differences range from
-2.07 s to +2.14 s. All selected tests, negative controls, bytecode hashes and
source restoration checks pass. These are edited builds, not unchanged-build
loops. The control makes small five-pair gains inconclusive; it does not establish
the cause of another experiment's regressions. Repeating all four actual
scratch-frame workflows yields 12/20 command wins; retaining the original run
gives 22/40 command wins and 33/40 execution-stage wins. The combined inlined
word64 command still regresses slightly, so scratch reuse stays archived.
[Identical-tool calibration](results/identical-tools-aa-e2e-01/summary.md).
[Actual comparison repeated](results/paired-temporary-frame-recheck-01/summary.md).
`scripts/bench_e2e_workflow.py --baseline-tool-key KEY --candidate-tool-key KEY`
can compare two retained builds while the working-tree engine stays unchanged.
The launcher builds the current working tree unless `--tool-key` selects a retained build.
[Runtime screen and tradeoffs](results/native-medium-copy-runtime-01/summary.md).
[All twelve edited workflows](results/paired-native-medium-copy-corpus-01/summary.md),
[fresh coverage](results/audit-execution-fre-native-medium-copy-01/summary.md).

Empty unit-call removal was implemented and tested, then archived. It wins 11/20
complete production-edit pairs; folded-trie execution saves 26 ms but the command
saves only 2 ms in the median paired comparison. Word64 and inlined word64 remain
mixed. All 106 bytecode tests and broad native checks pass, but the command results
do not justify further qualification. The guarded source and both rebuilt binary
hashes are restored exactly. Both actual VM binaries differed in this experiment;
a separate crossed screen retains both artifact/VM combinations.
[Empty-call results and decision](results/paired-empty-unit-call-compute-01/summary.md).

An opt-in unavailable-call experiment now runs 11 more original fre tests. Their
production-edit workflow first reproduced the cold-fast/warm-slower problem:
JIT 1.694 s versus native 1.523 s for median edited commands. A paired comparison
then raised guest MIR optimization from level 1 to level 3: JIT **1.739 → 1.308 s**,
with native at **1.671 s**. MIR3 wins all five edits against both, saving **358 ms**
per command versus MIR1 by the median paired difference. Strict type and borrow
checking remains enabled. The option stops at unavailable calls if reached;
successful tests avoid them. MIR tuning remains workflow-specific.
[Coverage, commands and limitations](results/unavailable-calls-capability-01/summary.md).

Wide-pointer equality is now implemented and qualified. It moves 62 lowering
failures to the function-expansion limit and leaves the 327 prior artifacts
identical; it adds no passing real tests yet.
[Correctness and workflow evidence](results/wide-pointer-capability-01/summary.md).

The retained JIT change emits native stores for small, proven local fills,
reducing returns from generated code to the interpreter. With the optional leaf
inliner enabled, it improves **14/15 paired compute build/test commands** and all
15 execution-stage comparisons. Median paired command savings are **163 ms** for
word64, **81 ms** for inlined word64, and **41 ms** for SHA-1. The remaining pair
differs by only 0.026 ms. Native remains faster on these compute workflows.

All eleven production-edit workflows pass with identical bytecode in both JIT
builds. Each uses five real production-body refactors, unchanged original tests,
and a deliberately wrong edit that every mode rejects. These medians include
Cargo, checking, export, launch, JIT construction and execution:

| Production-edit workflow | Native (s) | Baseline JIT (s) | Candidate JIT (s) |
|---|---:|---:|---:|
| [fre-word64](results/e2e-paired-fre-word64-jit-local-fill-02/summary.md) | 1.595 | 2.424 | 2.262 |
| [fre-word64-inline8](results/e2e-paired-fre-word64-inline8-jit-local-fill-02/summary.md) | 1.772 | 1.892 | 1.840 |
| [pgrust-sha1-inline8](results/e2e-paired-pgrust-sha1-inline8-jit-local-fill-02/summary.md) | 0.765 | 0.984 | 0.938 |
| [pgrust](results/e2e-paired-pgrust-jit-local-fill-broad-02/summary.md) | 0.649 | 0.533 | 0.526 |
| [fre-class-sequence](results/e2e-paired-fre-class-sequence-jit-local-fill-broad-02/summary.md) | 1.382 | 0.758 | 0.746 |
| [nushell](results/e2e-paired-nushell-jit-local-fill-broad-02/summary.md) | 0.670 | 0.480 | 0.476 |
| [ruff](results/e2e-paired-ruff-jit-local-fill-broad-02/summary.md) | 5.815 | 3.037 | 3.144 |
| [rg-aot](results/e2e-paired-rg-aot-jit-local-fill-broad-02/summary.md) | 0.540 | 0.199 | 0.194 |
| [nushell-type-relations](results/e2e-paired-nushell-type-relations-jit-local-fill-broad-03/summary.md) | 16.028 | 7.504 | 5.973 |
| [fre-grapheme-scalar-dfa](results/e2e-paired-fre-grapheme-scalar-dfa-jit-local-fill-broad-03/summary.md) | 1.298 | 0.818 | 0.808 |
| [fre-packed-literal-set](results/e2e-paired-fre-packed-literal-set-jit-local-fill-broad-03/summary.md) | 1.519 | 0.928 | 0.919 |

The candidate wins 39/55 complete-command pairs. The smaller and
frontend-heavy workflows are mixed; stage timings distinguish Cargo variation
from runtime effects. In particular, the large Nushell timing difference comes
from Cargo, while Ruff's median command regresses mainly in Cargo. Five samples
on a shared host are not confidence intervals or whole-suite results. Both builds
use strict checking and the same opt-in leaf inliner; leaf inlining remains off
by default.

[Full comparison and limitations](results/paired-jit-local-fill-corpus-02/summary.md)
retain every sample, source pin, cold/setup cost, and executed artifact. The
interrupted Nushell attempt and earlier Ruff artifact-order failure remain
separate from the completed comparisons. Downloads, tool bootstrap, OS-cache
coldness and reusable standard-library MIR setup are excluded from cold commands.
The [earlier three-engine corpus](results/e2e-simd-coverage-corpus-01/summary.md)
also compares the custom interpreter with native Rust.

## Use the custom engine

On the tested Apple Silicon macOS host, with the pinned `nightly-2026-09-08`
toolchain and Cargo dependencies available locally:

```sh
python3 scripts/interpreter.py \
  --manifest-path /absolute/path/to/project/Cargo.toml \
  --package my-crate --test-body --entry my_module::my_test --engine jit
```

Repeat `--entry` to batch zero-argument test bodies returning unit or
`Result<(), E>`. Use `--engine interpreter` for the custom interpreter. Some
standard-library paths require the optional `--std-mir` metadata sysroot.
Ordinary type checking, borrow checking, and diagnostics remain enabled.
[Setup and launcher details](INTERPRETER.md), [current architecture](JIT.md).

Guest code uses our lowering, memory model, interpreter, and machine-code emitter.
LLVM and existing interpreters do not provide a guest execution fallback. Native
Rust remains the separately measured reference. Partial frontend-checking modes
are explicit experiments, not the default.

The native-fill build has **88 passing bytecode tests**, **23,502 native
differential/rejection commands with inlining off and another 23,502 with it on**,
99 launcher checks, and all eleven production workflows. Local-fill tests cover
aliases, frame bounds, region splits, full-width live registers and exact budgets.
[Correctness gates](results/export-order-validation-01.json),
[same-artifact runtime comparison](results/jit-local-fill-runtime-01/summary.md).

The earlier standalone population-count candidate passed correctness checks but
was reverted: SHA-1 improved while both paired word64 build/test workflows slowed.
[Rejected experiment](results/paired-popcount-e2e-01/summary.md).

Two budget-register variants were rejected. The smaller frame slowed all ten
paired word64 edits; SHA-1 was essentially unchanged. The qualified block-linking
source and binaries were restored. [Negative result](results/paired-region-budget-leaf-e2e-01/summary.md).

Audit retention and built-in test metadata pass 79 focused checks. Byte table
lookup and ordered integer SIMD reductions pass 71 focused native/VM commands.
With explicit unavailable-call trapping, retained evidence now covers **242
original fre tests**: 231 reused by identical bytecode/VM hashes and 11 fresh
native/JIT passes. Another 78 stop at unavailable calls, 7 are ignored and 62
remain lowering-blocked. The option adds 76 focused checks and passes fresh
default validation, including 23,502 native differential/rejection commands.
Nushell's 162 retained programs still need custom-harness handling before execution.
[Audit usage](AUDIT.md), [capability evidence](results/simd-ordered-capability-01/summary.md).
[Next steps](RUNTIME-NEXT.md).

An additional `--inline-leaves` exporter experiment is now available, disabled
by default. It passes all eleven production workflows and fresh comparisons of
all 231 supported ordinary fre tests. It wins 35/55 paired edited commands;
word64 benefits are clearer than the mixed short and frontend-heavy workflows.
[Opt-in results and limits](results/paired-leaf-inline-corpus-01/summary.md).

Qualification also exposed an exporter ordering defect in Ruff: unchanged
source could produce different function IDs and constant offsets. Scheduling
function-pointer bodies in assigned-ID order fixes repeatability. Both compared
JIT builds include this fix; artifact equality remains a required check.
[Reproducibility evidence](results/export-determinism-01/summary.md).

Earlier experiments, including the separate Cranelift function cache and macOS
unchanged-executable publication issue, remain in [README history](README-HISTORY.md),
[JIT history](JIT-HISTORY.md), and [runtime history](RUNTIME-HISTORY.md).
The publication result is separate from the production-edit measurements above.
