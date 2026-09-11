# Reconsider MIR inlining after native Calls

The current custom runtime is source `aa2f6ea`, tool `0e94d6d8`. No guest
backend, exporter or wrapper implementation changes in this experiment.
The typed sample split puts 41.01% of folded and 12.23% of token thread samples
in guest-frame clearing. The hottest folded frame's original MIR locals occupy
16,704 of 18,224 bytes. Register initialization has zero sampled hits.

The existing eightfold MIR inlining budgets were chosen when guest Calls were
far more expensive. Test the hypothesis that ordinary inlining now improves
complete edited commands by reducing inlined code/local storage and frontend
work. This is not an assumption that smaller frames imply faster execution.
Do not implement aggregate alias/padding analysis or another clear-loop variant
before this comparison.

Use the existing workflow harness without changing its execution path. Its
`baseline` arm is the **proposed ordinary policy**, with exactly
`-Zmir-opt-level=3`. Its `candidate` arm is the **retained enlarged policy**,
with thresholds 400/800/240. These historical arm names are explicit; every
decision ratio is ordinary/enlarged (baseline/candidate), not the reverse.
Both arms use the exact installed 0e VM/exporter/wrapper, resumable Calls,
persistent registers, leaf inlining, strict Rust checking and the same
unsupported-call policy, guest limits and selected tests. Native uses LLVM O0,
incremental compilation, eighteen jobs and default libtest concurrency. Custom
Cargo uses four jobs. Keep the independent Cargo-check reference.

Run folded-literal-trie, then token-phrase, each with three rotated cycles of
five real production edits, original anchors and wrong-edit rejection in every
mode. Retain all 84 commands and 42 artifacts per workload, including negative
controls. Different compiler settings deliberately produce different artifacts;
the default runtime verifier remains strict. A separately supplied expected
flag map permits a compiler comparison only with identical tools and all other
runtime options, verifies actual child flags, and reports actual artifact
equality rather than claiming it. Qualify that path before timing begins.

Admission reserves four GiB of fresh caches with 20% growth, the eight-GiB
running floor, two GiB for a future first archive and 256 MiB of evidence:
15.05 GiB free before each workflow. This is conservative relative to the
completed fre history, not a reservation against unrelated shared-volume
writes. Preserve and stop on a space rejection; no cleanup or process control.

Predeclared decision: ordinary budgets must reduce median paired complete
wall time by at least **10% on folded**, with lower paired child CPU, and have
no **greater-than-5% wall or CPU regression on token**. Report all medians,
per-edit spreads, compiler stages, execution stages and cold commands. A pass
selects broader qualification; it does not automatically change defaults.
A failure is retained and stops this two-policy experiment; do not sweep
intermediate thresholds or rerun the same timings to seek a pass. The selected
seven-workflow controls and broad fre/TLS/native coverage remain subsequent
requirements for adoption. Unfiltered libtest support remains a separate gap.
