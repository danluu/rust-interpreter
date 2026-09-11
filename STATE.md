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
The `experiment/bounded-native-calls` branch now executes complete native trees
behind `--engine jit --jit-native-calls`. Default execution remains separate.
All 225 workspace tests pass (one ignored), including VM limit/fallback/profile
boundaries, TLS descendants and the standalone 64-frame ABI/copy checks.
[Check evidence](results/bounded-native-vm-03/summary.json). Seven CLI checks pass.
The failed `bounded-native-vm-02` check preserves an invalid-errno test fixture;
03 corrects its setup and passes. C allocation operations now enable JIT heap
addressing. No new performance result or installed release tool is claimed yet.

Next run the recorded full-workspace release check with tool installation, then
three-cycle folded/token real edit/build/test comparisons against b2aa6efe using
`--candidate-jit-native-calls`. Preserve predeclared gates and run held-out
workflows before retention. [Internal ABI](benchmarks/experiments/bounded-native-calls/INTERNAL-ABI.md).

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

Recent supervisors/controllers are terminal. `bounded-native-vm-01` passed 224
tests; `02` failed the new fixture; `03` passed all 225.
Their terminal receipts remain under `.work/experiments`; no task process is
currently running. Re-check actual identities before treating old receipts as live.
Detailed pointers/pins are in `.work/continuation-state.json`.

No subagents or independent model calls. No AWS activation, unrelated process
control, broad cache deletion, private cleanup or quarantine deletion. A separate
user-owned cleanup task uses the benchmark lock; wait without controlling it.
Serialize task builds/tests/benchmarks/cleanup under `.work/benchmark.lock` and
freeze measured inputs. Preserve original assertions, wrong-edit controls,
source restoration and historical evidence.
