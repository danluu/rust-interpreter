# Scratch-value availability: retain as a possible component

The test-only observer reconstructs all1,101/1,305 saved unprofiled functions
exactly, including words, maps, resume entries and assertion identities. All406
bytecode tests pass in each profile. The closure verifies229 distinct frozen
inputs and375 Git source bindings. No guest benchmark or executable publication
runs, and production emission is unchanged.

The bounded x9 observer finds2,671/3,087 additional eight-byte Load sites, weighted
182,563,140/143,445,029 times by the existing exact logical profiles. No executed
profile function is omitted. Nearly all originate in scalar Copy. This differs
from the earlier negligible virtual-register metadata-transfer hypothesis: x9
can retain the bits after the virtual source name disappears.

Coverage is not a latency result. About98% of affected Load sites are only three
machine words, including result publication that must remain. Their complete
spans cover50/1,651 and19/1,439 generated samples (3.03%/1.32%) in the two saved
short perturbed windows. The frequency-weighted static whole-operation fractions
are0.96%/0.85%; these include untaken paths in the denominator and are not retired
instruction counts or runtime bounds. See the separate bound cost report.

Do not run a standalone timing screen on these counts. Retain scratch forwarding
as a possible component while checking a larger source of memory traffic:
register flushing currently retains values live before the final operation even
when that operation already consumed their last use. Inspect exact flush spans
and CFG liveness first. Branch operands, unexecuted tree-call tails, fallback,
budgets, joins and backedges must remain correct. No optimization is adopted.

[Typed attribution](attribution.json), [cost and existing samples](../scratch-local-values-cost-01/summary.json),
[closure](closure.json), [build](../scratch-local-values-build-01/summary.json).
