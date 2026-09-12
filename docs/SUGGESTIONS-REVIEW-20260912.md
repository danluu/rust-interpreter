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
