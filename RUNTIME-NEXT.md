# Next work

The retained custom JIT still loses substantially to the specified native control
on the exhaustive token workflow. Repeated actual edits confirm this gap.
[Current evidence](STATUS.md), [review decisions](docs/SUGGESTIONS-REVIEW-20260910.md).

1. **Build on the completed current qualification.** Source `aa2f6ea`, tool
   `0e94d6d8`, passes 276 debug/release tests, 47,004 mixed native-validation
   commands, 245 TLS commands and 382 fre body replays with seven ignored.
   Both original compute gates pass: folded paired wall −21.82%, token −33.09%.
   A matched-frontend comparison isolates an additional 15.14% token gain from
   native copies. All seven held-out cases verify 588 commands, 105 pairs and
   294 artifacts, with no wall/CPU regression above 5%. The original zero-pair
   stop and aggregate schema failure remain preserved; neither caused a timing
   rerun. Both compute workloads still take longer than native Cargo, and
   whole-project compatibility remains unfinished. Keep options explicit.
   [Current results](results/resumable-copy-original-e2e-01/assessment.md),
   [held-out verification](results/resumable-copy-heldout-recovery-01/assessment.md).
2. **Choose the next execution change from fresh profiles.** The previous
   token profile put 88.19% of interpreted operations in copies; those copies
   now execute natively. Follow the [recorded profile protocol](benchmarks/experiments/resumable-native-calls/POST-COPY-PROFILES.md)
   on the exact current artifacts. Fresh captures now show 41.01% folded and
   12.23% token samples in clearing, with token boundary self only 2.23%.
   The typed arena split accounts for all clearing samples as guest memory;
   register clearing has zero hits, so a stronger register proof is parked.
   The ordinary/enlarged inlining comparison now fails both gates: ordinary
   paired wall +4.55% folded and +6.88% token, with higher CPU. Keep enlarged
   inlining and preserve all 168 commands and 84 artifacts. Follow the
   [broader aggregate byte-write plan](benchmarks/experiments/aggregate-reuse-census/BYTE-WRITES-NEXT.md):
   actual full-byte writes, partial writes/padding, alias exclusions and normal
   Call-return edges. The unchanged-code observer now finds 55.97% additional
   weighted byte scope folded and 31.90% token, passing the 25% folded gate.
   The separate [relocation experiment](results/aggregate-relocation-e2e-01/assessment.md)
   now passes 39 compiler tests, 1,024 native differential VM executions and
   both complete primary gates: folded wall −12.77%, CPU −12.89%; token wall
   +3.70%, CPU +3.33%. Both original assertions and all 168 measured commands
   verify. Compiler overhead outweighs the execution gain on token. Keep the
   candidate experimental pending [broad correctness and all seven held-outs](benchmarks/experiments/aggregate-byte-writes/QUALIFICATION-NEXT.md).
   Preserve exact budgets,
   initialization, fault order and guest state. Earlier narrow frame-reuse
   censuses are parked; their tiny measured opportunities do not justify a
   new optimization without evidence.
3. **Broaden useful execution.** Prioritize a recorded unfiltered suite attempt
   and the real unsupported behavior it exposes. Existing fre evidence runs
   bodies directly; it does not qualify libtest, unwinding, threads or OS/FFI.
   Add test/dependency/macro edits with original assertions. Generic API edits
   already have fifteen-cycle histories: pgrust −1.14% and Nushell +1.12% paired
   wall for the preceding call experiment, neither a material benefit.
   A shared test graph may improve selection reuse; eager export of every
   body is not assumed to be cheaper.
4. **Keep frontend work tied to measured costs.** Four-versus-eighteen-worker
   cold results fail the predeclared CPU bound; the tiny wrapper misses its
   separate cold gate. Neither is adopted as a standalone pipeline win.
   Native linker/backend alternatives remain unqualified. Preserve the current
   eighteen-job O0/incremental native control in comparisons, and label any
   new control configuration separately.
5. **Develop correct reuse before optimizing it.** The Nushell reduction and
   built-MIR observer locate history-sensitive literal allocation IDs in rustc
   incremental reuse. IDs are session-local, and equal bytes do not establish
   allocation identity. Cache keys need compiler/target/configuration, layouts,
   stable instance identities, semantic dependencies and relocations. With
   roughly 71 ms of lowering inside a 5.3-second Nu command, function reuse is
   parked as the immediate speed project. Keep guest state fresh and account
   for cache lookup, validation and loading costs.

Before each runtime experiment, record correctness gates, target workloads and a
meaningful complete-command performance criterion. Retain all regressions and
failed qualifications. A few milliseconds on five different edits do not justify
a broad speedup claim. Small opcode tweaks are no longer the default direction.

Native tiering is a possible explicit hybrid experiment, subject to the user's
custom-backend requirement. Its policy must account for missing/stale runtime
history, whole-target native compilation and duplicate work. It cannot promise
to match native on every command. Full panic unwinding and synchronization must
preserve Rust semantics; do not implement success-returning shims or skip cleanup.

Use only owned pinned checkouts; preserve assertions and source restoration.
Serialize task measurements under the benchmark lock. Never stop unrelated host
work to improve benchmark conditions. Clean only identified completed compiler
caches after ownership/live-file/artifact checks; preserve historical evidence.

[Earlier runtime plans and rejected experiments](docs/history/RUNTIME-NEXT-20260910-before-review.md)
