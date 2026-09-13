# Conditional frame-disjoint ranges justify a guarded prototype

All thirteen offline commands pass, with no guest execution: three adopted,
hash-bound profile censuses; byte-identical original, whole-CFG and strict-range
CLI results; and seven invalid-input/output-preservation controls. All admitted
functions complete within the bounds. Both debug and release qualification pass
470 workspace Rust tests, one ignored. The first admission timed out before
compilation; that receipt is retained separately.

| Saved workload | Strict best-group redundant checks | Conditional model | Subset requiring frame disjointness |
| --- | ---: | ---: | ---: |
| Token block | 24,339,008 | 265,026,216 | 249,987,240 |
| Token exhaustive | 383,172 | 4,320,512 | 3,956,149 |
| Folded short-window | 993,253 | 1,610,371 | 617,118 |

These are frequency-weighted, conditional opportunities. A group of N accesses
contributes N−1 to this count; the future guard itself costs more than a single
old check, and actual guard acceptance remains unmeasured. No emitted saving,
latency result or adoption decision follows from the counts.

The primary block test supplies a concrete mechanism. Generic SipHash c_rounds
has36 unknown accesses across32 bytes per native region, entered3,293,696 times;
d_rounds has108 accesses across32 bytes, entered1,071,616 times. The conditional
model covers all those accesses:115,279,360 and114,662,912 redundant checks.
Both depend on an entry frame-slot pointer, whose identity the strict analysis
loses after the first pointee write. Proving the pointee range disjoint from the
entire active frame can preserve that identity. Ignoring aliasing cannot.
The long d_rounds display truncates at64 sites explicitly; execution planning
must use a complete typed list and must never consume that truncated report.

Proceed with a generic guarded native-region prototype, initially on the
existing resumable path. Select by bounded typed structure and amortized check
count, never project/function name. Guard the complete range before any guest
progress; prove no wrap, correct arena/tag classification, bounds, readonly
requirements and current-frame disjointness. A failed guard must use original
ordered interpretation, preserving partial writes and eventual faults. Existing
resumable continuation validation and the VM's one-operation fallback make that
possible without weakening ordinary Jit::run's nonzero-progress contract.

Keep all original guest operations, overflow flags, budgets, liveness and memory
cache effects. Test actual native guards against an independent boundary oracle,
plus self-aliases, linked entries/backedges, ABI, copied ranges, exact budgets and
fault ordering. Only after correctness and real-profile qualification should a
fresh changed-source primary screen run. All five full guards remain mandatory
for adoption; a failed screen cancels unstarted cases.

Evidence: [summary](summary.json),
[qualified executable](../disjoint-frame-build-02/summary.json),
[unstarted first admission](../disjoint-frame-build-01-admission/summary.json),
[prospective census scope](../../benchmarks/experiments/disjoint-frame-census/PLAN.md).
