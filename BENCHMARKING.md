# Benchmark methodology

## Current custom interpreter/JIT workflow

`scripts/bench_e2e_workflow.py` measures complete commands after five cumulative
production-body refactors in owned, pinned project snapshots. It retains all
selected original tests unchanged, first verifies that every engine rejects a
wrong production edit, and restores source afterward. Native and custom modes
each use one command with `--batch`. Warm results are edited build/test commands.
The custom engines keep ordinary type and borrow checking and execute through
the project's bytecode interpreter or direct AArch64 emitter.

For example, the complete eighteen-test folded-trie workflow uses:

```sh
python3 scripts/bench_e2e_workflow.py --project fre --workflow folded-literal-trie \
  --batch --std-mir --trap-unsupported-calls --inline-leaves \
  --guest-mir-opt-level 3 --instruction-limit 100000000000 --run-id NEW_RUN_ID
```

Paired comparisons use `--baseline-tool-key`, `--comparison-engine jit` and,
when isolating runtime changes, `--expect-identical-bytecode`. Match leaf inlining
with `--baseline-inline-leaves`. Every executed bytecode artifact is retained.
Explicit guest MIR flags apply to custom modes; native keeps its test profile.
Five shared-host pairs are not confidence intervals. Separate medians of stages
need not sum to a median total, or equal a median paired difference.

Use `--cycles 3` or more for repeated edits. Each cycle rebuilds original source,
checks the wrong edit, and replays all five real edits. Only the first original
command is cold; later original commands are labeled anchors. Each mode must
have a different source hash from its preceding compilation. Three cycles rotate
every edit through all three mode positions. Reports include child user/system
CPU time, paired differences and per-edit min/median/max; these are descriptive
measurements, not confidence intervals. Cache history evolves across cycles.

The [first repeated token run](results/paired-repeated-token-01/assessment.md)
demonstrates why both source and artifact hashes matter: corresponding engines
produced identical bytecode, but returning to the same source after the first
cycle changed constant/data layout. Do not assume identical source implies an
identical artifact across different compiler-cache histories.

`--cargo-timings` enables Cargo's compilation-unit reports in every mode. Report
generation stays inside the command timer. The harness copies each report after
timing and records its hash under the raw run's `cargo-timings/` directory. These
reports help distinguish selected-target compilation, other compiler invocations
and time before compilation begins. Treat such runs as diagnostic comparisons;
they include report generation. [Cargo's timing-report documentation](https://doc.rust-lang.org/cargo/reference/timings.html).

## Controls, setup and interpretation

The harness now accepts `--native-profile repository|o0-incremental`, `--jobs`,
`--native-jobs`, `--native-test-threads N|default` and repeatable
`--native-rustflag=ARG`. The explicit O0 profile overrides optimization and
incrementality for native dev/test builds; it leaves panic policy alone. Flags
are passed as separate encoded Cargo arguments. Settings appear in each report.

`--check-floor` adds a separately timed `cargo check --lib --profile test` after
each primary triplet. It has its own target directory and source history, and
does not execute tests: the deliberately wrong runtime edit still checks
successfully. Exporter frontend, lowering/export and individual pass timings
are reported separately. Pass times are nested in lowering/export; missing
timings are marked unreported. Do not add nested stages together.

The [paired control qualification](results/paired-native-controls-pgrust-02/summary.md)
and [interpreter/JIT qualification](results/e2e-native-controls-reference-01/summary.md)
each completed 63 primary commands and 21 check commands. These are harness and
configuration checks on the pgrust hash library, not the nine-project result.

`scripts/bench_workflow_corpus.py` runs the nine entries in
`benchmarks/workflow-corpus.json` serially. It uses three cycles, an O0/incremental
native candidate with 18 jobs/default test threads, four custom build jobs,
and the checking reference by default. These are explicit candidate settings,
not an assertion of the fastest native setup. For example:

```sh
python3 scripts/bench_workflow_corpus.py --run-id controls-new --only pgrust \
  --candidate-tool-key b2aa6efe746cf00d40703af478c750c49c2d07eb11508c2b28d08122f17b15cc \
  --baseline-tool-key 57a54edd6b64db0e7a1a854dfb42ec0d519cde40366be977fe26d51bb1e16497
```

Omit `--only` for the full corpus. To survive a client disconnect, prefix the
command with `python3 scripts/supervise_experiment.py --run-id SUPERVISOR_ID --`.
Receipts retain exact child identities and commands under `.work/experiments`.
The runner waits a bounded time for the benchmark lock, retains failures and
does not stop other processes or perform automatic cache cleanup.

Current repeated comparisons use `--native-profile o0-incremental`,
`--native-jobs 18` and `--native-test-threads default`, with four custom build
jobs. The legacy single-workflow CLI still needs these explicit options;
omitting them selects repository settings, four jobs and one test thread.
Record explicit changes to optimization, incrementality,
linker/backend, compiler workers, build jobs and test concurrency. A tuned control
must preserve the selected behavior and diagnostics; unsupported native backend
configurations are reported separately. Never select a fastest configuration
post hoc for each measured edit and call it a deployable policy.

Report frontend/link dominated workloads separately from workloads with material
guest execution. Mixed win counts are bookkeeping, not a general speedup result.
An independent Cargo-check command measures a frontend reference; it is not a
semantic substitute for code generation and does not prove the residual stage
cost by subtraction of noisy wall times.

The pinned corpus is in `benchmarks/corpus.json`: pgrust, Ruff, Nushell, fre and a
private local rg-aot adapter. Only task-owned snapshots are edited. Preserve
assertions, exact source hashes, failed controls, raw commands, artifact hashes
and source restoration. Private source and diagnostics remain under `.work`;
only approved aggregate reports are committed.

Toolchain installation, dependency fetching, engine builds and optional std-MIR
preparation occur before the timed commands and must be labeled as setup. The
first command uses empty per-run Cargo targets. This is target-cache cold, not
OS-cache cold or installation-cold. Do not clear machine-wide caches.

Use the project benchmark lock to serialize this task's builds, tests, benchmarks
and compiler-cache cleanup. Freeze measured sources and scripts during a run.
Record exact owned subprocess identities and child CPU. Do not stop, reprioritize
or signal other sessions or workloads to manufacture an idle host. Load averages
are context; they do not remove shared-host noise or establish causality.

A useful comparison repeats the same edits through balanced orders while
preserving each mode's own cache history. Report per-edit distributions, whole
session totals, stage times and CPU; do not hide setup or slow samples. Use
same-workflow A/A runs to assess variability before fine-grained decisions.
Bootstrap intervals or significance statements require a design that accounts
for distinct edits and correlated cycles, not just an increased row count.

Before a runtime experiment, state the target workloads, correctness gates and
meaningful complete-command improvement required. Exact within-pair bytecode is
required to isolate runtime changes. Across cache histories, retain actual
artifacts and report identity differences explicitly.

## Reproduction references

- [Token workflow](benchmarks/TOKEN-PHRASE.md)
- [Current measurements and evidence](STATUS.md)
- [Repeated source-cycle assessment](results/paired-repeated-token-01/assessment.md)
- [Earlier native-cache/publication methodology](docs/history/BENCHMARKING-20260910-before-review.md)

The earlier protocol includes historical LLVM/Cranelift, linker and unchanged
publication commands. Those experiments keep their original profiles and limits;
their settings are not silently applied to the current custom-engine results.
