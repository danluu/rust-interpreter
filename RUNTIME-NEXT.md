# Next work

Use [STATUS.md](STATUS.md) for measured controls and
[the September12 review](docs/SUGGESTIONS-REVIEW-20260912.md) for every new
suggestion. Historical experiments retain their original decisions.

1. **Parallel-suite screen complete.** The token complete-command screen
   passes:34.3% lower wall time,3.2% more CPU, all40 commands and restoration
   controls. Candidate median5.330s versus retained custom8.021s; it still
   takes2.216× the paired two-process native control. Folded and pgrust
   guards also pass. Qualify ordinary Cargo/libtest controls before a default change. Every worker owns
   its JIT and every test starts fresh. One worker remains the default.
   [Result](results/parallel-suites-edit-token-01/assessment.md),
   [comparison](benchmarks/experiments/parallel-suites/WORKFLOW.md).
2. **Measure one composed optimization.** Qualify fixed clearing, whole-call
   expansion, budget-register/call-slot changes and persistent function reuse
   together. Keep prepared execution and custom worker counts fixed between
   routes. Freeze actual component sources, current and historical anchors,
   original selections, A/A controls, fifteen edited pairs and held-outs
   before timing. Modest correct components may enter the composition without
   separate8% gates. The complete build must earn its material8% wall target,
   CPU and held-out guards. Do not infer gains by multiplying old ratios or
   retime an unchanged failed component until it passes.
3. **Strengthen native controls.** Include ordinary Cargo/libtest with default
   test concurrency, plus explicit isolated controls where semantics require
   them. Include a practical line-tables control without demanding an8%
   optimization gate for it. Keep repository defaults and debugging tradeoffs
   visible. Use matched explicit Cargo workers on this shared host. Large
   Ruff/Nushell linker/debuginfo and always-encode-mir calibration remain
   targeted follow-ups; old controls are not relabelled as fastest native.
4. **Choose implementation from complete-command costs.** After composition,
   prioritize resumable call preparation/transfer and unchanged-function
   binding/graph passes. Preserve readiness, fault/budget ordering, initialized
   registers, relocations and strict checking. Audit obsolete trees/stubs
   before a substantial call rewrite. Native retired-instruction attribution
   should guide later VM-side allocation or memory-model design; samples and
   virtual-slot counts alone do not predict elapsed-time gains.

Shared-call specialization, tagged-address reshuffling and other unchanged
failed candidates stay parked. Seeded differential coverage is implemented;
use it to qualify the new composition rather than starting another census.
Full libtest/unwind/guest-thread and arbitrary-project support remain open.

Preserve source, tools, profiles and executed artifacts. Keep compact new
results and local raw evidence under [RETENTION.md](results/RETENTION.md).
The user authorized safe local cleanup and declined another volume. Retire
only exact completed disposable public caches as needed for scheduled work;
leave private data and other workloads alone. Storage work is not optimization.

Merge qualified changes to main and push regularly to the private
`danluu/rust-interpreter` repository. Parked sources remain accessible.
