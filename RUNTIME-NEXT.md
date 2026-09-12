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
3. **Confirm the next runtime opportunity on current artifacts.** The original
   exhaustive test process retires7.132× native instructions and4.398× cycles,
   with lower CPI. That favors instruction-volume work but does not identify
   which emitter change saves time. The historical operation profile points
   to indirect calls and allocation primitives among VM returns; a three-test exact census is now running
   on current integrated token/folded artifacts before implementing a bridge
   or dispatch change. Measure actual fast-path use if revisiting capacity design. Preserve
   readiness, ownership, fault order, exact budgets and strict checking.
   Do not repeat negligible width packing or tagged-address check shuffling.
   [Counter scope](results/process-instruction-counts-01-completed/assessment.md).
4. **Keep frontend work tied to its own costs.** Main's invocation-local
   compiler reuse is integrated. The latest token comparison records about
   139ms rebinding within642ms baseline lowering. Resolve the binding cost
   before choosing lazy allocation identities or a new cache format; green
   bodies do not make session-local compiler allocations reusable unchanged.
   Full-catalog selection and launcher lookup remain later usability/latency
   work, with original checking and artifact identity requirements intact.
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
