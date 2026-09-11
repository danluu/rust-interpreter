# Continuation checkpoint — September 11, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test measurements. Every suggestion in
`suggestions.txt` has an explicit [decision](docs/SUGGESTIONS-REVIEW-20260910.md).
The user's file remains unmodified and untracked. Local Git commits are authorized;
no remote or push was requested.

Current runtime source is `a2a0e04`, tool `b2aa6efe`: 188 bytecode, 11 exporter
and 3 historical-cache tests passed. The completed new nine-workflow corpus uses
that tool. The broader 47,004 native differential commands, TLS checks and
382-body fre replay still belong to `57a54edd`; they were not rerun on this fix.
[Exact build index](benchmarks/tool-builds.json).

## Completed and checked in

- `267ad90`: all nine stronger-native workflows completed, with 756 commands,
  189 independent Cargo checks, 378 artifact checks and restored source pins.
  [Assessment](results/native-controls-corpus-01/assessment.md). Native uses root
  O0/incremental, 18 jobs and default test concurrency; custom builds use four
  jobs. Package overrides remain. Linker/backend/worker alternatives are unqualified.
- Token edited commands remain 6.664 s custom versus 2.002 s native; folded is
  2.485 versus 1.638 s. All outliers and all three fre cross-history layout
  differences remain recorded. No semantic equivalence or cause is established.
- Native-call censuses `01` and `02` passed eight and nine diagnostic tests and
  matched saved instruction/call totals. Current census sources are in `267ad90`;
  the first version is reconstructible using its verified reverse patch.
- The expanded census finds bounded acyclic call trees with explicit terminal
  Trap support cover 80.72% of token direct calls / 59.02% of their frame bytes;
  folded is 54.61% / 17.55%. These are scope counts, not speedup predictions.
- Generated STATUS/index and all assessments are current. Corpus recovery
  receipts now clear stale child identity/exit fields; this fix followed the
  measured run. `97dbe1a` preserves the call ABI audit.

## Next action

Implement the [bounded native call-tree experiment](benchmarks/experiments/bounded-native-calls/PLAN.md).
Experimental source `09de2a9`, tool `c98d995b`, executes complete native trees
behind `--engine jit --jit-native-calls`. The default engine remains separate.
All 225 workspace tests pass in debug and release (one ignored); seven CLI
checks and both saved real workload smoke checks pass. [Release/tool evidence](results/bounded-native-release-01/summary.json).
[Smoke assessment](results/bounded-native-real-smoke-01/assessment.md). The Git
build index verifies the new source key and installed binaries.

The first native-call E2E corpus is complete: 168 commands, 30 edited pairs,
84 paired artifacts, restored sources. Token improves 14.4% paired (6.504 to
5.565 s marginal medians); folded regresses 3.0% paired (2.559 to 2.603 s).
Both original targets fail. [Assessment](results/bounded-native-e2e-01/assessment.md).
Do not retain or enable this intermediate candidate by default. The seven held-out
workflows and broader native/TLS/fre qualification were not run on it.

The `experiment/native-region-calls` branch now links outer direct Call stubs
with ordinary JIT regions behind `--jit-native-calls --jit-native-call-stubs`.
All 231 workspace tests and seven CLI checks pass. The earlier modes remain
available. [Implementation/ABI notes](benchmarks/experiments/bounded-native-calls/REGION-CALLS-NEXT.md).
Source `26833c3`, optimized tool `2f31c6a0`, passes the same 231 workspace tests
in release and both saved real-artifact smoke checks. The three-cycle folded/token
E2E comparison `native-region-e2e-01` is running against b2aa6efe with both native
flags. Keep c98d995b as an intermediate comparison; the original gates and broader
qualification remain. [Release receipt](results/native-region-release-01/summary.json).

A whole-tree budget bound avoids partial budget exits only if every target and
all storage are ready before entry. Otherwise decline before progress or use a
real continuation. Preserve argument-copy errors before depth errors, return
copy before truncation to the aligned callee base, aliases, exact budgets,
initialization, guest limits and profile accounting. Untaken traps still need
correct native failure handling. [ABI audit](docs/NATIVE-CALL-EXPERIMENT.md).

The predeclared experimental target is 20% lower paired token command latency
and 10% lower folded latency, CPU improving too, with no unresolved >5% held-out
regression. Broader execution qualification is required for production retention.

## Process and ownership

The first tree E2E corpus, both native-region workspace checks, optimized build
and saved-artifact smoke are terminal with return code zero. The region E2E
supervisor is PID 11215, controller 11220, initially folded child 11225;
recorded identities/commands are in `.work/experiments/native-region-e2e-01/`
and `.work/corpus-runs/native-region-e2e-01/status.json`. Re-check live state
before treating these PIDs as current. Frozen benchmark scripts must stay fixed
until this corpus finishes. Detailed pointers/pins are in `.work/continuation-state.json`.

No subagents or independent model calls. No AWS activation, unrelated process
control, broad cache deletion, private cleanup or quarantine deletion. A separate
user-owned cleanup task uses the benchmark lock; wait without controlling it.
Serialize task builds/tests/benchmarks/cleanup under `.work/benchmark.lock` and
freeze measured inputs. Preserve original assertions, wrong-edit controls,
source restoration and historical evidence.
