The completed build screen passes its fixed gate: token median paired
build-to-ready wall time improves **5.306157%** and build CPU improves
**5.784833%**. Pgrust wall time increases **0.955303%** and CPU increases
**0.800187%**, within the fixed 5% regression guards. All six history guards
pass. **Public Ruff and Nushell confirmations are PENDING.** This branch is an
experimental integration for review, not an adoption decision.

| Public case | Edited pairs | Median candidate/baseline wall | Median candidate/baseline CPU |
| --- | ---: | ---: | ---: |
| fre token-phrase-allocation | 15 | 0.9469384262216509 | 0.9421516729634383 |
| pgrust default | 15 | 1.0095530334540133 | 1.0080018747736423 |

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
The integration starts at fetched main `955a19d`; its compiler and Cargo/build
inputs have no changes relative to the measured baseline `c1c3b3a`. Later owned
scalar-output, writer-scratch and epoch-alias candidates are excluded. Existing
results and the baseline top-level validation summary are preserved.

Both benchmark arms and the full differential qualification used the frozen
baseline VM SHA-256
`03d401c1df926f99941cdd5325c2d58848d25e3b774ffa7f27db20b448c65a20`
and wrapper SHA-256
`56fec5a315571ba8308f5c2b637aff8b8be200ba84cde1ba7c606f61e47606d3`.
The candidate exporter is
`2a33492691a047483e010314a215bc3861ca733225fc8d9cac14b85cc289065c`.
The candidate build also produced a separately linked VM with hash `1301b8b...`;
that VM was recorded but was not selected for this experiment. The full built
and selected identities are in [the tool manifest](evidence/owned-analysis-tools.json).

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
and at most 5% aggregate pgrust regression. The passing screen permits the
already fixed public confirmations: one three-cycle Ruff default history with
all six original tests and one three-cycle Nushell generic-interface history
with all fourteen original tests. Each confirmation must remain within 5%
paired build-wall and CPU regression, using the same tool/VM/options and full
wrong-edit, bytecode-identity and restoration controls. Their frozen
[plan and command vectors](evidence/owned-analysis-public-confirmation-plan.json)
and controller/assessor sources are included; live or incomplete confirmation
observations are not copied into this draft.

These shared-host edit-history results support further confirmation of general
compiler build-time reuse. They do not establish cold-build, whole-command,
runtime or unknown-holdout speedups. The earlier parked candidates remain in
their original reports and are not pooled with this screen.

See [measurement.json](measurement.json),
[qualification.json](qualification.json),
[independent-audit.json](independent-audit.json) and
[evidence.md](evidence.md) for exact ratios, controls and provenance.
