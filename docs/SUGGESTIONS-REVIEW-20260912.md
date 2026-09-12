# September 12 latency review

This reviews the replacement user-owned `suggestions.txt`, SHA256
`5621e45439cafaa3dbd8ba22eafaaa654c3be8fcaa0e6b0754b3cafad5146964`.
The file is unchanged. This disposition supersedes the earlier review's
optimization priorities; completed experiments keep their original decisions.

The main criticism is valid: independent 8–10% screens can exclude useful
components before their combined effect is measured. A correct component with
a modest measured benefit can enter a prospective composition experiment.
It does not need a separate 8% win. The composed build must earn adoption
against a fixed retained anchor, with fresh controls and held-outs. Historical
failed gates are not retroactively passes, and multiplying their ratios is not
a measured or reliable prediction of the combined gain.

The just-completed [parallel-suite edit screen](../results/parallel-suites-edit-token-01/summary.json)
passes all 40 complete commands, wrong-edit/restoration checks and unchanged
test-source checks. Across five production edits, the median paired wall ratio
is0.65687 and CPU ratio1.03237. Candidate median5.330s, retained custom8.021s,
two-process native2.422s and serial native3.119s. The candidate is still2.216×
slower than its paired native control. These are twelve original token tests,
not the older three-test selection. It is a screen, not broad adoption evidence.

## Decisions on each proposal

| Item | Decision, constraint and next action |
| --- | --- |
| 0 Stage analysis | Accept the separation between frontend-dominated and compute-heavy cases. Keep stage scopes and source selections attached to every number. Separate medians need not add; the check-to-export residual is not a causal experiment. The older three-test token row cannot be substituted for the current twelve-test suite. |
| 1.1 Small wins | Accept the policy criticism. Correctness is necessary; it does not establish a repeatable performance benefit. Use smaller mechanisms as composition candidates rather than requiring each to clear8%. |
| 1.2 New retention rule | Adopt prospectively: use fresh same-session A/A controls and fifteen edited pairs to assess the composition. A/A envelopes describe observed noise, not confidence intervals. Keep a material8% composed wall target against the fixed anchor, CPU and held-out guards, all pairs and source-restoration controls. Small components may be included without individual performance acceptance; no repeated trials to seek a pass. Parallel scheduling has an explicit CPU tradeoff, separately from emitter efficiency. |
| 1.3 Compose now | Highest optimization priority after closing the current suite comparison. Port and qualify fixed clearing, whole-call expansion, budget-register/call-slot changes and persistent function reuse together, with prepared execution fixed on both sides. Verify actual source differences before calling this a composition. The earlier “fixed-clear combined” experiment combined clearing with newer interpreter code; it did not measure this proposed stack. Do not promise a one-hour port or a15–19% result. |
| 2.1 Fixed clearing | Include in that candidate; do not merge alone based on its old7.39% result. Its broad existing correctness qualification guides regression coverage, but new composition still needs checks. |
| 2.2 Call sequence | Next runtime implementation after composition. Preserve target readiness, fault ordering and independent frame/register/working-memory limits. A single slack comparison is only valid with a proof covering alignment and overflow. Check all helper clobbers before retaining x16. Frame bytes and virtual registers occupy different buffers: their clearing is not two passes over the same storage. Descriptor elision requires proof that a callee cannot exit, fault or consume its budget. |
| 2.3 Fewer transitions | Include the bounded whole-call mechanism in composition. Keep constant-argument specialization parked. Raising inlining budgets is a new later hypothesis with an export-cost/code-size budget, not a free improvement. |
| 2.4 Budget register | Include the existing correct implementation in composition; further changes belong with the call rewrite. Preserve exact tail execution and errors at small instruction limits. Its old1% result cannot be replaced by a9–12% sampling estimate. |
| 2.5 VM allocation | Worth investigating after instruction attribution. Moving work to the JIT does not eliminate it: each process and parallel worker can pay it again. Restrict analysis to functions actually compiled and measure preparation plus execution. The census predicts only2.55–3.60% additional resident reads on the two token tests;94% fewer virtual slots is not94% fewer memory operations. Preserve logical budget semantics and interpreter agreement. |
| 2.6 Copy/zero emission | Inspect alongside the call rewrite. Use wider transfers only after proving exact range, tail and overlap behavior; preserve source fault order. No separate tiny-candidate timing campaign. |
| 2.7 Memory model | Design after instruction attribution; stop tagged-check reshuffling. Guard pages and readonly mappings cannot by themselves enforce sub-page object bounds, lifetime or logical memory budgets. Preserve defined VM faults instead of turning them into host faults. |
| 2.8 Retired instructions | High-value diagnostic if existing permitted local counters expose both native and custom execution. Verify counter availability and equal measured scopes first; sampling PCs are not retired instruction counts. No profiling-service activation or changes to other workloads. |
| 3.1 Cache binding | Next exporter priority after the composition result. Reduce unchanged-function binding/decoding/publication, retaining dependency and relocation validation. An mmap format needs versioning, bounds and lifetime checks. A source edit still requires strict checking and correct invalidation. |
| 3.2 Aggregate relocation | Make proven green function results reusable. Separate expensive pass work from formatting a few diagnostic lines; do not attribute157ms to logging. Make optional diagnostics explicit when touching this path, while preserving required benchmark receipts. |
| 3.3 Graph passes | Incrementalize only where the dependency closure proves unchanged inputs. Inlining and CFG results may depend on callees; “green body” alone does not prove an unchanged final function. |
| 3.4 Selection/catalog | Accept as a usability experiment: one checked catalog per source state, selection without another frontend where a complete retained graph exists. Full-target lowering can increase cold/edit cost and encounter unsupported unselected bodies. Represent per-entry support honestly and measure both real edits and selection changes separately. |
| 4.1 always-encode-mir | Accept a controlled large-target experiment after native calibration. Record each host/target unit and its reachable MIR requirements; require original tests and identical frontend checks. Do not simply remove MIR from dependency units needed by export. |
| 4.2 Dependent checks | Do not use runtime reachability to omit required type/borrow checks. Trait resolution, features, macros and exported metadata can change outside a selected runtime graph. Investigate only compiler-proven metadata equivalence or a Cargo-compatible dependency reduction that preserves strict checking. |
| 4.3 Launcher paths | Accept a bounded later optimization, particularly for rg-aot. Key resolved paths on toolchain/environment identity and invalidate correctly. Measure changed-source commands; do not turn unchanged-build timing into the goal. |
| 4.4 Hash/write duplication | Accept eliminating redundant reads and copies, while retaining a check binding the executed bytes to the catalog. One producer-supplied hash cannot replace validation at every necessary trust boundary. Review the existing artifact-digest branch before implementing overlapping work. |
| 5.1 Cargo workers | Correct for the older4-custom/18-native histories. Current parallel experiments use two Cargo workers for every mode because the host is shared. Future cold comparisons should use matched explicit worker counts and expose a throughput preset; do not overwrite old controls or assume an idle18-core host. |
| 5.2 Native concurrency | Accept the stronger control. The completed screen compares explicitly isolated semantics with one/two workers; it does not represent fastest native execution. Future adoption measurements will include ordinary Cargo/libtest with its default test concurrency as the primary native control, plus explicit isolated controls when needed. Keep suite workers explicit until folded/pgrust guards and that control are qualified. |
| 5.3 Prepared default | Candidate for the development preset. It preserves fresh guest state and saves repeated preparation, but default changes need the same selected-suite guards and clear scope. It is already enabled on both custom routes in the current comparison. |
| 5.4 Cross-command code | Defer behind exporter binding and call work. Cache keys must include compiler/backend/CPU/ABI/options and stable dependency identities; native relocations and executable-memory ownership must be rebuilt safely. About0.1s token compilation is a smaller opportunity than guest execution or lowering. |
| 5.5 Per-test setup | Agree: stop optimizing a few milliseconds in isolation. |
| 6.1 Native debuginfo | Accept line-tables as an explicit practical control without demanding an8% optimization gate. Retain the repository-default control and explain the debugging tradeoff. Do not replace or relabel old observations. |
| 6.2 Large native calibration | Accept. Compare a predeclared available linker/debuginfo configuration on Ruff or Nushell with the same real edits, tests and Cargo workers. Do not claim fastest-native behavior from the current controls. |
| 6.3 Native stages | Partly implemented: the original135 edited commands already have a documented rounded suite/residual split. The new isolated runner records build and per-test times. Ordinary libtest comparisons should retain native build/run stages from the same command; do not label residual time pure compilation. |
| 7.1 Interpreter work | Agree: it improves the reference/interpretation mode, but does not count as a JIT complete-command win. |
| 7.2 Diagnostic feature | Reasonable after the measured candidate: move optional census binaries/modules behind a feature while keeping necessary runtime logic and coverage enabled in qualification. Do not disrupt frozen builds for cosmetic build-size work. |
| 7.3 Old call modes | Audit CLI, artifact and test users before removal. Separate retirement from the first composition so benchmark differences are interpretable. Remove obsolete paths before a substantial call-protocol redesign, preserving the reference interpreter. |
| 7.4 Storage work | Agree it is maintenance, not optimizer progress. The user explicitly requested safe cleanup after declining another volume. Completed Nushell audit metadata retirement recovered8.55GB of actual free space and enabled the current edit benchmark. Perform only cleanup necessary for scheduled work, preserve evidence and private caches, and avoid new archival infrastructure. |
| 8 Order | Close current guards; qualify the composed candidate and stronger native controls; measure the composition once; then choose call-protocol or exporter-binding work from its end-to-end costs. Large native/MIR calibration and instruction attribution follow as targeted diagnostics. |

## Immediate execution

1. Done: token, folded and pgrust pass all120 commands; the native
   disadvantage remains explicit in the combined result. Required cache
   cleanup is complete. No additional storage work is queued.
2. Freeze a composition manifest from the actual component sources. Use
   current strict frontend/selection semantics, prepared execution, and fixed
   worker counts across custom routes. Include the retained9637b0ac anchor
   on its original selection and the current selected-suite anchor so gains
   are not credited merely to different test sets or scheduling.
3. Qualify the composed code before timing. Predeclare the native controls,
   A/A schedule, fifteen edit pairs, guards, storage budget and stopping rule.
   Existing failures remain historical evidence; this is one new combined
   implementation, not another trial of an unchanged failed candidate.

Relevant evidence: [fixed-clear composition scope](../benchmarks/experiments/frame-initialization/FIXED-INTEGRATION.md),
[whole-call result](../results/whole-call-primary-02/assessment.md),
[whole-call costs](../results/whole-call-costs-01/assessment.md),
[reuse screen](../results/export-reuse-screen-token-01/decision.json),
[allocation census](../results/register-lifetimes-census-01/assessment.md),
[native stage limits](../results/native-existing-stages-01/assessment.md).

## Execution update after the reviewed proposals

The suggestions file still has the hash recorded above. Several originally
missing comparisons are now complete; their results change the next priorities.

| Suggestions | Completed work and disposition |
| --- | --- |
| 1.1–1.3, 2.1, 2.3, 2.4 | The corrected composition completed all528 original/wrong/edit/restored commands. Its original three-test token selection improved11.59%, but the twelve-test selection improved4.91% and missed the composed gate. Folded and pgrust guards passed. Retain both selections and the observed noise; do not multiply component ratios or rerun this candidate to seek acceptance. The old fixed-clear proof needed an alignment correction, so its earlier test successes were insufficient reason to merge those exact bytes. |
| 2.2, 2.6 | The first call-protocol rewrite completed all462 commands. Token improved1.62% against composition, below its3.81% A/A wall envelope; both guards passed. The next implementation replaces repeated capacity checks with a conservative native credit, while preserving independent frame limits, overflow/alignment checks on refill and exact exits. It passes422 Rust tests per profile,102 harness checks,7 exact tests,9 suite commands and203 strict cache/native checks. All462 edit commands now pass their expected outcomes. Token gains0.55%, within4.65% wall A/A; folded gains0.56% but exceeds the CPU-noise bound. Pgrust passes its guard. Keep the runtime experimental without retiming. |
| 2.5, 2.8 | Three complete native/JIT pairs show7.132× retired instructions and4.398× cycles in the custom process. This measures the whole test process, including preparation, and is not a Cargo timing or pure guest count. It favors instruction-volume work over an assumed stall explanation. The existing weighted width-packing census found negligible additional resident reads; do not restart that rejected proposal. Upper-word store elimination would need a separate traffic census and an initialization/exit proof. |
| 3.1–3.3 | Main's invocation-local compiler reuse is integrated and qualified in the experiment's baseline and candidate. Its prior build-to-ready improvement is not a whole-command result. The integrated baseline records about139ms of persistent rebinding on token; inspect actual resolution/allocation/patch work before choosing lazy binding or a new file format. The current cache already reuses green function templates; compiler allocation identities still require current-session resolution. |
| 4.1, 6.1–6.3 | The large Nushell native calibration completed88 commands with14 original assertions. Line tables improved paired wall3.85% and CPU2.57%; repository settings and observed A/A remain visible. This is a practical native control without an8% optimizer gate. A host-only MIR-encoding experiment is still open; guest dependencies must continue to carry MIR, and runtime reachability cannot replace strict checking. |
| 5.1–5.3 | Current full comparisons use two Cargo workers on every route, two prepared custom workers, and ordinary native libtest concurrency. Scheduling/preparation stays fixed between custom candidates. No unmatched18-worker cold claim or new default adoption follows from these measurements. |
| 7.1–7.4 | No interpreter-only speedup is credited to the JIT command, no additional storage cleanup is needed, and no frozen benchmark inputs were changed for optional-code retirement. |

Capacity-credit comparisons are complete. The separate host-MIR wrapper now
passes16 routing tests per profile,19 process checks,20 real Cargo/command
checks and five driver tests. Its Nushell edit comparison is active, followed
by mandatory pgrust and conditional Ruff guards. Keep this large-project
frontend investigation distinct from compute-heavy runtime work; the unchanged
VM/exporter isolates the wrapper effect.

Evidence: [composition](../results/composed-development-edit-token-03/stage-assessment.md),
[original selection](../results/composed-development-edit-anchor-01/stage-assessment.md),
[call protocol](../results/resumable-call-protocol-edit-token-01/stage-assessment.md),
[instruction accounting](../results/process-instruction-counts-01-completed/assessment.md),
[width weighting](../results/jit-register-width-weighted-01/assessment.md),
[Nushell native control](../results/large-native-nushell-02/assessment.md),
[capacity qualification](../results/call-capacity-credit-coverage-01/summary.json).
