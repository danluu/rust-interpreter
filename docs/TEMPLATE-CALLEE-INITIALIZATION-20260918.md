# Experimental template cache: callee initialization dependency

Two controls reproduce a correctness bug in the experimental cross-program native
template cache. A caller embeds whether each callee needs its registers cleared,
but the old key recorded callee layout and scalar-entry facts without that derived
boolean. A body edit can change the initialization requirement without changing
those other inputs, allowing stale caller instructions to be reused.

The staging control changes a callee from writing a register before use to reading
its initial zero value. Freshly emitted caller words differ, yet the old key is
identical. The execution control first fills reused register storage through a
sibling call, then invokes the edited callee. Cached execution incorrectly fails
its zero-value assertion; fresh JIT and the custom interpreter pass. The fixture
also covers scalar-call settings, persistent registers, history verification and
alternating original/changed Programs once corrected.

Source4ee4f999 runs30646/30649; both controls fail as expected with exit101 and the
controller completes successfully. Closure40201/40204 verifies their exact sources
and outputs. [Reproduction](../results/template-callee-initialization-reproduction-01/summary.json).
These failures are retained evidence, not an accepted correctness qualification.

The correctionaffb4716 binds the exact precomputed initialization boolean consumed
by resumable_call and changes the internal key domain tov3. Existing code/entry
budgets, scalar/ assertion relocations and current-owner bindings remain. Review
also checks direct-callee argument sizes, frame/result/register layout and scalar
eligibility/extent/step counts/current targets. This is not a formal completeness
proof. Full runtime qualification and actual parser verification pass; closure records bind the exact sources and binaries.

The adopted runtime has no cross-program native-template history and is unaffected.
Earlier experiment results still describe their recorded inputs; their successful
replays do not establish correctness for all callee-body edits. Suspend further
reuse performance work until the corrected key passes its controls and real suites.
The diagnostic input-phase extension is qualified but its parser replay is deferred.

Corrected qualificationaffb4716 passes654Rust tests in each profile with16ignored,
33diagnostic integration controls and a feature-off VM build. The exact prior
442Python/22skip record is reused after unchanged script/test bindings.36owned
sessions and69clients are reaped. Qualification60783/60786 is closed91574/91577.

The corrected actual parser replay completes95866/95869:16suites,1,824original
invocations and16,299independently verified template hits. Outcomes and the wrong
edit's exact assertion text match; current kernel CPU reconciles. Hit totals depend
on worker assignments and history contents; their difference from earlier replays
is not an isolated measurement of the key correction. No timing comparison or
adoption follows from this correctness fix.

[Qualification](../results/template-callee-initialization-qualification-01/summary.json),
[verified replay](../results/template-callee-initialization-parser-client-01/summary.json).
Resume diagnostic input/constructor attribution using the corrected diagnostic
binaries, with verification disabled only for phase measurement. Earlier missing-key
binaries remain historical evidence and must not be used for future candidate work.
