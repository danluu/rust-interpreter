# Next work

Use [STATUS.md](STATUS.md) for measured controls and
[the September12 review](docs/SUGGESTIONS-REVIEW-20260912-2210.md) for every new
suggestion. Historical experiments retain their original decisions.

Current action: complete the primary-first scalar Copy comparison. The emitter
uses existing proven local ranges and reduces local Copy8 from seven words to
three. It passes441 Rust tests per profile,125 current harness checks and222
real correctness/profile commands. Its40-command screen passes with wall−5.46%
and CPU−3.47%, beyond4.84%/2.57% A/A. The full five-case comparison has started
with token; no adoption until all required gates and final audits pass. The
selection came from current Copy sample shares of24.34%/18.26%, with all3,985
generated samples assigned. Keep the original screen separate from full pairs.
Post-execution maps pass436 Rust tests per profile,
103 harness checks and10 real-test commands; all three current generated code
dumps and per-PC profiles match the adopted runtime exactly.
The433-test direct-operand candidate passed its40-command screen, but the full
154-command token comparison finds wall+0.78%/CPU+0.06%, inside4.84%/2.25% A/A.
Its primary gate fails. Keep the runtime experimental and the other four cases
unstarted; do not retime it. The immediate shift/rotate screen
completed40 commands with all original outcomes and artifacts matching, but
wall+0.90%/CPU+1.19% gives no gain against3.07%/3.00% A/A. Keep that runtime
experimental and cancel its unstarted guards; do not retime the screen. Current samples show
generated code dominates both token tests. The separate binding diagnostic
passes complete off/on artifact histories and attributes93.32ms to current-MIR
context, but only4.83ms to indexing. Park the positions-table rewrite; lazy MIR
must avoid work rather than move it between phases. Runtime candidates use
predeclared screens and cancel unstarted guards on primary failure; adoption
still requires every declared guard.
[Direct-operand final decision](results/direct-operands-full-01/assessment.md),
[Verified operation maps](results/operation-map-validation-01/assessment.md),
[Operation attribution](results/operation-map-sampling-01/assessment.md),
[Scalar-copy screen](results/scalar-copy-operands-screen-token-01/assessment.md),
[Full protocol](benchmarks/experiments/direct-operands/FULL.md),
[Shift screen decision](results/immediate-shifts-screen-token-01/assessment.md),
[Binding decision](results/replay-costs-token-02/assessment.md),
[current native regions](results/current-runtime-costs-01/assessment.md),
[adopted composition](results/memory-lookup-main-complete-01/assessment.md).

Completed comparison context: the new composition combines memory operands
and compiler-identity lookup caching. The earlier memory-only comparison
completes all462 token/folded/pgrust commands. Its refined runtime passes428 Rust
tests per profile,131 harness checks,7 exact tests,9 suite commands,203 strict
native/cache checks and3 profiles. Logical work at every PC is identical to
the wide control; generated code is5.1–5.6% smaller. Token improves6.60% wall
and5.93% CPU and passes; folded passes its guard. Pgrust's CPU ratio to the
anchor plus A/A is1.05389, exceeding1.05. Keep that failed adoption decision
and do not retime it. The next composition targets frontend overhead in pgrust
while retaining the measured token component. It needs new full-command
measurements and large/private guards, not multiplied historical ratios.
[Mechanism and qualification](results/memory-operands-profile-01/assessment.md).
The new composition passes 138 harness tests and 20 strict real Cargo checks.
Its 726-command controller completed Nushell, private rg-aot, token, folded and
pgrust. Every mandatory case and the final frozen-input checks passed before
source integration. No other own build, test or profile ran alongside timing.
[Prospective comparison](benchmarks/experiments/memory-lookup/WORKFLOW.md).
Nushell now completes 132 expected commands and passes its regression margin;
its 0.93% wall change is inside 5.73% A/A and is not an established speedup.
Private rg-aot also completes 132 expected commands and passes, improving
wall 12.55% and CPU 11.53% beyond 2.46%/1.61% A/A. Both large/private guards
pass. Token completes all 154 commands and passes: wall improves 7.66% and CPU
6.78% versus wide, with 5.25%/3.94% A/A; wall improves 18.35% versus the fixed
anchor. It still takes 1.894 times ordinary native Cargo. Folded and pgrust
also pass their guards. No completed case will be retimed.

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
   Nushell comparison completes396 commands, with identical runtime/compiler binaries
   and strict checking in every custom arm. Pgrust passes with wall−5.96%
   and CPU−5.16%. Private rg-aot improves13.18% wall/11.67% CPU but misses
   its3% CPU-noise limit (observed3.67%). Nushell changes wall−0.54% and
   CPU−0.91%, with6.56% wall noise exceeding4%. Keep the failed overall
   adoption decision and do not retime.
   Bounded guarded indirect-call specialization is complete;
   [design](docs/INDIRECT-CALL-NEXT.md). It passes424 tests
   per profile,123 harness checks, seven exact tests, nine suite commands and
   203 strict native/cache checks. Three profiles preserve every logical PC
   count and confirm1.03million/0.74million native indirect calls in the two
   dominant tests. Full edited-command comparisons against the wide-operation
   baseline and fixed anchor complete token with wall−1.44%/CPU−0.97%, below
   4.75% wall A/A; the component gate fails. All462 expected commands complete.
   Folded fails its wall margin; pgrust passes the documented margin but fails
   the frozen executable's extra CPU ceiling. Both rules were required
   prospectively before the held-outs. Keep the failed adoption decision.
   The subsequent paired-register candidate also completes462 commands;
   token gains0.71% wall, below1.77% A/A, and both held-outs pass. It remains
   experimental. The typed address-check census then finds zero fully reusable
   checks in all three profiles, with no analysis declines. Do not implement
   that cache. The current candidate instead simplifies existing memory
   operands, retaining all checks and full VM-register writes.
   Full-catalog selection remains later work;
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
