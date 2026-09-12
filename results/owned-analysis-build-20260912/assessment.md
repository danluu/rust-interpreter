This compiler change passes the fixed build screen and both public confirmation
guards, qualifying it for production review. Token median paired build-to-ready
wall time improves **5.306157%** and build CPU improves **5.784833%**. Pgrust
wall time increases **0.955303%** and CPU increases **0.800187%**, within its
fixed 5% guards. Ruff and Nushell also remain within their fixed 5% wall/CPU
regression guards. All planned histories and outliers are retained.

| Public case | Edited pairs | Median candidate/baseline wall | Median candidate/baseline CPU |
| --- | ---: | ---: | ---: |
| fre token-phrase-allocation | 15 | 0.9469384262216509 | 0.9421516729634383 |
| pgrust default | 15 | 1.0095530334540133 | 1.0080018747736423 |
| Ruff default confirmation | 15 | 0.9915148181922369 | 1.0021751172664355 |
| Nushell generic-interface confirmation | 3 | 0.9829978671363502 | 0.991181500510191 |

Ruff's median wall improvement is **0.848518%**, with CPU **0.217512%** higher.
Nushell improves wall **1.700213%** and CPU **0.881850%**. Ruff contains fifteen
edited pairs and Nushell only three; they provide different amounts of evidence
and are evaluated separately. No pooled confirmation median or additional
per-cycle gate was introduced. The worst Ruff pair, cycle 1/state 4, remains
included at wall ratio **1.1693303287** and CPU ratio **1.1477729356**; the fixed
confirmation guard applies to each complete case's median.

The metric ends immediately before VM dispatch and includes launcher work and
waited build children. CPU is `build_to_ready_cpu.total_seconds`. These values
are medians of the paired ratios across all edited states, not ratios of overall
medians. Cold anchors, wrong edits and final restoration checks remain in the
record but are excluded from edited medians. No A/A noise was subtracted.

The candidate combines invocation-local compiler work reuse with ownership of
existing compiler data. It retains the scalar frame planner's local certificate,
normalized local types and initialized shapes, and the pre-planner eligibility
result for promotion. Leaf inlining moves storage from the owned program after
preparing the original call graph. Aggregate coverage finalization consumes its
private read/write ranges. Liveness analysis reuses a completed block transfer
only when its successor union is unchanged, charging the exact original logical
work so budget decisions stay identical. Independent certificate checks,
callee-ABI resolution, arithmetic bounds, rollback and fallback paths remain.
No persistent cache schema or bytecode format changes are included.

These are the exact compiler and test sources from `04bb082`, including its
earlier local-analysis components. All 137 staged compiler-source files match
the frozen measured manifest and reproduce tool key
`eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d`.
The integration starts at fetched main `955a19d` and retains subsequent upstream
report/status updates through `a21fac1`. Upstream compiler and common inputs
remain unchanged relative to their measured versions. Existing results and the
baseline top-level validation summary are preserved.

Both benchmark arms and the full differential qualification used the frozen
baseline VM SHA-256
`03d401c1df926f99941cdd5325c2d58848d25e3b774ffa7f27db20b448c65a20`
and wrapper SHA-256
`56fec5a315571ba8308f5c2b637aff8b8be200ba84cde1ba7c606f61e47606d3`.
The candidate exporter is
`2a33492691a047483e010314a215bc3861ca733225fc8d9cac14b85cc289065c`.
The candidate build also produced a separately linked VM with hash `1301b8b...`;
that VM was recorded but was not selected for this experiment. Its exact bytes
were separately retained before later build-target reuse; the
[preservation receipt](evidence/owned-analysis-built-vm-preservation.json)
records its retained path and full hash. The full built and selected
identities are in [the tool manifest](evidence/owned-analysis-tools.json).

Qualification recorded **388 Rust tests passed, zero failed and one ignored in
each debug and release profile**, followed by **23,727 differential validation
commands** with the selected tools. The local-layout fixture supplied 111 native
results checked by both interpreter and JIT, and its unchanged standalone oracle
retains the earlier successful 261-input receipt. The full command archive and
all 24 pre-screen proof hashes are retained. Source-only independent reviews
and the independent screen audit found no blocker; no new builds or tests were
run to assemble this integration.

The controller completed all 12 planned benchmark/verifier commands in order,
covering three independently initialized one-cycle histories per project.
Every history included compiler-success/runtime-assertion failure for the wrong
edit and a fresh build and execution of the actual restored original after
leaving the source-edit context. The six histories contain 144 fresh primary
compilations, 48 independent checking controls, 30 edited pairs and 96 retained
executed artifacts. Paired bytecode was identical in every state. The audit
checked the twelve distinct comparison caches, source transitions, test sets,
mode order, raw launch metrics, CPU sums, artifact hashes and tool/source/common
bindings. There were no interruptions, partial histories or repeated histories.

The [prospective plan](prospective-plan.md) requires at least 5% token wall
improvement with improving CPU, at most 5% wall/CPU regression in each history,
and at most 5% aggregate pgrust regression. The two already fixed confirmations
then completed: one three-cycle Ruff default history with all six original
tests, and one three-cycle Nushell generic-interface history with all fourteen
original tests. Both use the same tool/VM/options and full wrong-edit,
bytecode-identity and restoration controls. Their frozen
[plan and command vectors](evidence/owned-analysis-public-confirmation-plan.json)
and exact completed controller/assessor evidence are included.

The confirmations add 96 primary commands, 32 checking controls and 64 retained
executed artifacts. Ruff accounts for 66/22/44 and Nushell for 30/10/20,
respectively. All four planned benchmark/verifier commands completed once,
sequentially, without interruption. Every wrong edit compiled before failing
an original test: Ruff's `check_code_serialization` and Nushell's
`test_any_is_top_type`. Each history freshly rebuilt and executed the actual
restored original after the source-edit context exited. Independent source
reconstruction reproduced every state hash and confirmed that the entire
original test module stayed byte-identical in all states.

Every baseline/candidate artifact pair is identical within its source state.
Both confirmations have some different artifact bytes across cycles, as the
original verifier records; cross-history identity or equivalence is not claimed.
The audit rehashed all 64 retained confirmation artifacts, checked exact
commands, tool/common/source bindings and readiness CPU/wall boundaries, and
independently reproduced all eighteen edited-pair ratios and the fixed decision.
Both confirmations pass their complete-case guards, with no exclusions,
subtraction, retiming or replacement histories.

These shared-host edit-history results support this general compiler build-time
reuse change under the fixed public protocol. They do not establish cold-build, whole-command,
runtime or unknown-holdout speedups. The earlier parked candidates remain in
their original reports and are not pooled with this screen.

See [measurement.json](measurement.json),
[qualification.json](qualification.json),
[independent-audit.json](independent-audit.json),
[confirmations.json](confirmations.json),
[confirmation-independent-audit.json](confirmation-independent-audit.json) and
[evidence.md](evidence.md) for exact ratios, controls and provenance.
