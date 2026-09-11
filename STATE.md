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

The `experiment/native-region-calls` branch links outer direct Call stubs with
ordinary JIT regions behind `--jit-native-calls --jit-native-call-stubs`.
Source `26833c3`, tool `2f31c6a0`, passes 231 workspace tests in debug/release,
seven CLI checks and both real-artifact smoke checks. Its completed 168-command
E2E corpus improves token 19.3% paired but regresses folded 1.4%; both original
gates fail. [Assessment](results/native-region-e2e-01/assessment.md). All five
pins and 84 paired artifacts were reverified. Keep the options experimental.

Fresh three-window profiles of that exact candidate pass original assertions.
Folded: 48.1% generated, 21.9% frame reservation, 12.0% native boundary and
9.3% dispatcher self. Token: 61.7% generated, 11.2% native boundary and 10.4%
dispatcher self. These are perturbed sample shares, not gain predictions.
The diagnostic code dump is implemented in `059d818` / `7ad1ccdb` and passes
233 workspace tests in debug/release. Exact same-process bytes and ranges resolve
all generated samples: token has 14.0% direct register-array stores and 11.7%
native zeroing; folded 6.0% stores and 8.2% native zeroing. VM frame reservation
remains 23.1% in the folded diagnostic. These are sampled shares, not savings.
[Next implementation](benchmarks/experiments/bounded-native-calls/VALUE-LIFETIMES-NEXT.md):
full-CFG liveness and up to three persistent u128 register pairs across native
edges, with correct VM spill/reload and complete native ABI preservation. Keep
frame lifetime/layout changes separate. Do not repeat parked argument-zero or
unused-local work. Current branch is `experiment/native-code-profile`.

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

All E2E, release and three-window sampling runs are terminal with return code
zero. The profile-report helper initially rejected a relative test-fixture path;
the corrected helper passes synthetic partition/error checks and reproduces
all three historical generated sample totals. The first exact-code token capture missed the JIT arena during startup; two
windows succeeded and all three test runs passed. The bounded readiness-wait fix
and complete token retry/folded captures are preserved. No task process is active.
Detailed evidence and pinned identities are in `.work/continuation-state.json`.

No subagents or independent model calls. No AWS activation, unrelated process
control, broad cache deletion, private cleanup or quarantine deletion. A separate
user-owned cleanup task uses the benchmark lock; wait without controlling it.
Serialize task builds/tests/benchmarks/cleanup under `.work/benchmark.lock` and
freeze measured inputs. Preserve original assertions, wrong-edit controls,
source restoration and historical evidence.
