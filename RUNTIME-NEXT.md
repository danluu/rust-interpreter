# Next work

Use [STATUS.md](STATUS.md) for measured controls and
[the September12 review](docs/SUGGESTIONS-REVIEW-20260912.md) for every new
suggestion. Historical experiments retain their original decisions.

1. **Keep the completed host-MIR decision.** Wrapper466c60a2 completed all264
   Nushell/pgrust commands with matching artifacts and original assertions.
   Nushell paired wall+0.35% and CPU+0.31% show no gain;4.13% A/A wall also
   exceeds the4% quality bound. Pgrust passes its regression guard. Ruff was
   conditional and is not admitted. The wrapper stays experimental without
   retiming; the gate already allowed component gains smaller than8%.
   [Nushell assessment](results/host-mir-edit-nushell-01/assessment.md).
2. **Keep the completed runtime decisions.** Composition completed528
   commands; its original three-test token selection improved11.59%, but its
   twelve-test selection missed adoption. The call-protocol rewrite completed
   another462 commands without a useful gain beyond noise. Capacity credit
   completed all462 commands: token wall−0.55% against integrated baseline,
   versus4.65% wall A/A, and−7.34% against the fixed anchor. Folded's CPU-noise
   guard also failed; pgrust passed. These runtimes remain experimental.
   Modest correct mechanisms were composed and measured; their old ratios are
   not multiplied or their failed gates retroactively changed.
   [Latest token result](results/call-capacity-credit-edit-token-02/stage-assessment.md).
3. **Retain the completed wide-operation result.**
   The current-artifact census passes all six control/profile commands and
   finds4.84million interpreted128-bit bitwise/shift operations in the dominant
   block-boundary test,71.5% of its interpreted operations. The custom emitter
   now handles And/Or/Xor/Shl/Shr. All419 tests/profile,106 harness checks, seven exact selections, nine suite
   commands and203 native/cache checks pass. Three current profile replays
   reduce block interpreted operations from6.77million to1.93million with
   exact logical work/memory/entropy. Token completes154 commands and passes: wall−4.55%, CPU−3.25% versus
   integrated baseline; wall−12.05% versus fixed anchor; wall A/A2.39%. It
   remains1.957× ordinary native. All462 commands now pass expected outcomes.
   Pgrust passes its guard; folded wall−0.74%/CPU−0.06% shows no measured
   regression, but its3.65% CPU A/A exceeds3%, so adoption does not pass.
   Keep the runtime experimental without retiming. Keep the exhaustive token test in the selection;
   it has far fewer such operations. Counts do not predict a time saving.
   [Current census](results/current-runtime-boundaries-02/assessment.md),
   [qualification plan](benchmarks/experiments/wide-bitwise/PLAN.md).
4. **Keep frontend work tied to its own costs.** Main's invocation-local
   compiler reuse is integrated. The latest token comparison records about
   139ms rebinding within642ms baseline lowering. Resolve the binding cost
   before choosing lazy allocation identities or a new cache format; green
   bodies do not make session-local compiler allocations reusable unchanged.
   The optional compiler-identity lookup cache passes115 harness checks,
   20 real Cargo checks and seven driver tests. Its fixed pgrust/rg-aot/
   Nushell comparison is running, with identical runtime/compiler binaries
   and strict checking in every custom arm. Pgrust passes with wall−5.96%
   and CPU−5.16%. Private rg-aot improves13.18% wall/11.67% CPU but misses
   its3% CPU-noise limit (observed3.67%). Keep that failed gate, finish
   Nushell and review the complete evidence without retiming.
   The next compute-bound design is bounded guarded indirect-call
   specialization; [design](docs/INDIRECT-CALL-NEXT.md), no implementation yet. Full-catalog selection remains later work;
   original checking and artifact identity requirements remain intact.
5. **Use the stronger native controls already established.** Every current
   comparison uses matched two-worker Cargo and ordinary native libtest
   concurrency. Nushell's completed88-command native calibration found3.85%
   lower paired wall time with line tables; a native control needs no8%
   optimizer gate. Retain repository settings and debugger tradeoffs. No
   fastest-linker,18-worker cold or unchanged-build claim follows from it.
   [Native calibration](results/large-native-nushell-02/assessment.md).

Shared-call specialization, tagged-address reshuffling and other unchanged
failed candidates stay parked. Seeded differential coverage is implemented;
use it when qualifying the next runtime implementation.
Full libtest/unwind/guest-thread and arbitrary-project support remain open.

Preserve source, tools, profiles and executed artifacts. Keep compact new
results and local raw evidence under [RETENTION.md](results/RETENTION.md).
The user authorized safe local cleanup and declined another volume. Retire
only exact completed disposable public caches as needed for scheduled work;
leave private data and other workloads alone. Storage work is not optimization.

Merge qualified changes to main and push regularly to the private
`danluu/rust-interpreter` repository. Parked sources remain accessible.
