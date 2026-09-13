# Next compute-bound candidate: guarded indirect calls

The guarded implementation on `experiment/guarded-indirect-20260912` now
passes 424 debug and release tests, 123 Python checks, seven exact real tests,
nine suite commands and 203 native/cache checks. All three current profile
replays preserve every logical PC count, memory peak and recorded entropy.
The block-boundary test executes 1,025,924 of 1,025,947 indirect calls natively
with 23 published thunks; the exhaustive test executes 737,989 of 843,776 with
21 thunks. Folded has only 28 native indirect calls and is an overhead guard.
[Current profiles](../results/guarded-indirect-profile-01/assessment.md).

Tool `9e219e2e` retains the wide-operation exporter/wrapper. The complete
154-command token comparison changes paired wall−1.44% and CPU−0.97%, below
4.75% wall A/A, so it misses its prospective component gate. The full stack
improves12.44% wall against the fixed anchor but takes1.768× ordinary native.
Keep this runtime experimental and do not retime it to seek a pass. Folded and
pgrust remain mandatory; folded first encountered a zero-command lock timeout.
[Completed token](../results/guarded-indirect-edit-token-02/stage-assessment.md).

The earlier52-command token attempt stopped at its disk floor and was kept
without a verdict. Cleanup preserved protected artifacts; the completed run
used fresh caches, the same frozen rules and no partial-pair reuse.

Prepared qualification also shows fewer VM entries, so first-target retention
has not eliminated all benefit in that mode. Its fresh and prepared contexts
have different logical totals; those receipts alone cannot establish a
controlled test-order effect. Avoid another cache-size experiment until current
sampling identifies a material cost. Re-examine generated instruction work and
host-side allocation/binding costs before choosing another implementation.
[Prepared counts](../results/guarded-indirect-prepared-counts-01/assessment.md).

The first host build stopped at two existing test fixture initializers missing
the new cursor pointer. Both fixtures were corrected; the failed receipt stays
recorded alongside the successful second build.
[Build](../results/guarded-indirect-build-02/summary.json),
[exact selections](../results/guarded-indirect-qualification-01/summary.json),
[strict controls](../results/guarded-indirect-cache-01/summary.json).

The current-artifact census found1,025,947 interpreted indirect calls in the
token block-boundary test and843,776 in the exhaustive test. The block test's
largest site is `RawTableInner::find_inner`, with948,377 calls. Native wide
operations removed the larger bitwise boundary count; this makes indirect
calls a plausible next target. Counts do not establish time or monomorphism.
[Current census](../results/current-runtime-boundaries-02/assessment.md).

Current native resumable transitions support direct Call and Return. They
already preserve exact budgets, initialized register storage, argument-copy
order, alignment padding, independent memory/depth limits and checked result
copies. Indirect calls exit to the VM, which validates the full function
handle, argument sizes and result size before constructing the callee frame.

Prefer reusing that checked direct-call emitter after observing a valid target,
instead of introducing dynamic frame descriptors and a second call protocol.
The alternative would load callee layout and signature metadata on every
indirect edge and would need new dynamic-copy, clearing and limit proofs.
Static expansion over every signature-compatible function risks code growth;
the function signature alone does not identify the actual target.

Proposed first version:

1. Allocate bounded, stable dispatch slots only for indirect call sites in a
   prepared function. A slot is initially empty. Native code checks the slot
   and exits at the original PC when empty, without charging the operation.
   Keep this table separate from native resume entries to avoid making a stub
   jump back to itself. No executable instruction is patched while running.
2. After the VM validates a function handle and its signature, permit at most
   one specialization for that caller function/PC. Generate a small thunk
   containing a full128-bit equality guard for that exact handle and the
   existing direct resumable-call sequence for its validated callee layout.
   A mismatch returns to the original VM path without charge or state change.
   Different targets do not cause an unbounded sequence of recompilations.
3. Stage code and all metadata before publishing the slot. Update only on the
   creating thread between native entries, while no generated frame is live
   on the host stack. Include tables and thunks in explicit capacity budgets;
   failed admission leaves the empty slot and ordinary VM behavior intact.
   Cold or code-declined callees still use the existing readiness decline.
4. Reuse each caller's register-allocation, spill and argument-location data.
   Do not substitute a new caller layout or a generic spill convention. Preserve
   the large-register-offset scratch-register rules of the existing emitter.
   A prepared suite may retain the specialization between tests, but every
   invocation rechecks the handle and all guest state remains fresh.

Qualification must cover alternating and changing valid targets, incompatible
signatures, invalid and nonzero-high-word handles, unready and declined callees,
code/table exhaustion, budget exhaustion before and during a call, fresh and
reused registers, aliasing arguments, mixed alignment, exact memory/depth limits,
returns to interpreted instructions, and profiled PC counts. Compare against
the interpreter and independent native Rust expectations using valid programs;
all mismatch/failure behavior must preserve the original VM semantics.

Then replay the exact current saved assertions and entropy streams. Record
published thunks, native hits, remaining VM calls, compile cost and code size;
the VM count combines first use, mismatches and other declines. a single-target
assumption must be measured, not inferred from the function name. Only a
qualified implementation proceeds to full changed-source token comparisons,
including both dominant tests and all mandatory held-outs. Freeze a fresh
prospective gate before timing and retain the previous wide-operation decision.

This adds lazy machine-code specialization only. Rust type and borrow checking
remain complete before any guest execution.
