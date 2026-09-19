# Option-hash Ruff mechanism screen

Prospective development screen. No timing has run and no future exporter identity is bound. This screen follows the passed compiler/runtime/std checks and must wait for actual exporter frontend/publication checks and the fresh strict sixteen-call Ruff history. The original strict-warm-build protocol still controls final latency and fresh-holdout claims.

Use the qualified standalone `R/experiments/workflow-runtime-arms-01/bench_e2e_workflow.py` with its ordinary verifier. Keep Ruff's pinned source, manifests, dependencies, six tests and five cumulative production edits unchanged. Both custom modes use JIT, MIR optimization level 3, leaf inlining, resumable calls, persistent registers, the existing instruction/allocation limits, and HIR capture/reuse disabled. Both compatibility switches remain absent. Function and borrow-check caches retain their ordinary disabled configuration. The compiler change is the immutable option-hash cache; there is no application-specific optimization.

Run exactly two complete fresh histories, in this order:

1. A/B: original compiler/runtime/std/tools versus the qualified option-hash compiler/runtime/std/tools. Initial mode order is native, baseline, candidate.
2. A/A: two separately cached instances of the unchanged original compiler/runtime/std/tools. Initial mode order is candidate, native, baseline.

Each history has one original build, the deliberately wrong edit, all five valid cumulative edits once, and restoration. Each mode has its own initially empty project cache; histories share installed tools and downloaded dependencies only. Use the existing within-history permutation machinery, one cycle, jobs 2 for every mode, the repository native profile, pinned nightly-2026-09-08 native toolchain and one native test thread. Do not enable Cargo timing HTML, incremental-info or self-profile instrumentation. Do retain the existing build-to-ready and whole-command wall/CPU measurements and every command's output and artifact identity.

The actual candidate tool key, successful strict result and complete commands must be bound and reviewed before execution. Require exact off/on bytecode agreement in the preceding correctness history and exact paired bytecode agreement for this semantics-preserving compiler change. Failures are retained; no prefix splicing, replacement of slow samples, unchanged retries or additional samples after observing results.

Report all five valid edited observations per arm, paired candidate/baseline ratios, native results, cold/setup/restoration costs and session totals. For the fixed screen decision, let B be the median of the five paired A/B complete-command ratios, and V the median of the five absolute deviations of the A/A complete-command ratio from 1. Continue performance qualification only if B + V < 1. Report build-to-ready comparisons separately without substituting that earlier boundary for complete-command latency. A miss parks this unchanged candidate's performance path; it does not justify weakening checks or changing the decision rule.

This is a mechanism screen, not the final fifteen-observation gate. Even five sub-0.5-second observations would not establish the campaign target. Use complete successful command time as the conservative strict readiness bound; never subtract execution time. Fresh holdout sources and measurements remain sealed until the development qualification gate passes.

Serialize actual work with the shared canonical benchmark lock, using the existing bounded 600-second admission and at least 16 GiB free before each history. Keep a 9 GiB active-child stop threshold and 8 GiB floor. Preparation must bind fresh owned namespaces and verify a finite allocation/evidence budget without silently expanding it. Record host contention and preserve slow samples; do not control peer processes or clear shared caches.
