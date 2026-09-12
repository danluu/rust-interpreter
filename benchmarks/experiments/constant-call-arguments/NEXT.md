# Apply folding where call arguments make it useful

The corrected general folder passes368Rust tests per profile, the18-command
standalone fixture and exact saved-program checks. Its34real-test replay gains
only2.63% runtime on token, about0.17s, versus about0.30s of offline folding.
The real edit screen stopped before any build; there is no measured end-to-end
ratio. Keep the global pass off main and deprioritize a standalone retry.

This amends the earlier requirement to complete the general folder's real edit
screen before investigating clones. Its limited runtime gain and export cost
already make it a poor standalone prospect. The next candidate applies the
qualified folder only to bounded specialized callees. Measure that candidate
separately, starting from the retained exporter without global folding. No
performance adoption follows from the saved runtime numbers.

Use only typed, statically proven argument bytes at direct Call sites. Reuse the
conservative block-local fact analysis, including the null-read correction.
Retain original functions, entry IDs, indirect calls, layouts and the call ABI.
Argument validation and copies still happen before entering a clone. Initialize
clone entry facts in argument-copy order; an unknown overlapping argument must
invalidate known bytes. Every clone uses the existing edge certificate and
per-artifact fault/budget rules. Do not infer heap pointees or initial zeroes.

First prototype: reuse common signatures of at most three known scalar arguments
of1/2/4/8bytes, seen at least twice at the same callee. Rank by static site reuse
and proven operation reduction, with deterministic ID/value ties. Limit each
callee to four clones, the whole program to64clones/16,384new operations and5%
code growth. Restrict candidate bodies to512operations and bound all analysis
and signature work. A clone must remove at least eight operations and25% of its
body after folding/CFG cleanup. Keep unique caller-location signatures out by
the reuse requirement. No function names, project names or dynamic profiles
participate in compiler decisions.

Build clones from original bodies before redirecting original direct-call sites;
do not recursively specialize generated clones. On a shape/work/growth decline,
keep the original call. Preserve all runtime memory writes and potential faults.
Share the existing function CFG cleanup without reoptimizing every original body.

Start with differential bytecode checks for common and conflicting signatures,
overlapping argument slots, caller mutation, null/invalid argument pointers,
indirect and recursive calls, aliased outputs, budgets and decline limits. Then
measure static coverage and runtime on the existing full token/folded/pgrust
artifacts. A promising candidate still needs real changed-source native/check/
control/candidate commands, strict type/borrow controls and exact whole-artifact
verification. Keep the existing10%token wall/no-CPU-regression screen and5%guards;
broader projects follow only after those gates. Resource stops are incomplete.
