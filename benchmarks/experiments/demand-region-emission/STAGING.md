# Offline single-region staging

Reuse one FunctionAnalysis and stage exactly one existing region, including
Call/Return transitions. Every other region emits no words. Reconstruct full
functions first; combine separately staged fragments in their original order,
replace only declared successor branches with full-function targets, and require
all original words, entries, assertion identities and operation spans to match.
Unresolved edges remain pointed to their own VM fallback tails. Check self-edges,
backedges, unsupported successors, budget/assertion/fault tails, size splits and
per-fragment code-limit refusal. No executable memory is allocated by this model.

This intentionally still scans earlier regions to consume range-analysis work
in the original order, and allocates dense temporary entry vectors. It is a
correctness model, not the runtime demand implementation. Those costs must be
removed before benchmarking. It neither patches published code nor retains
analysis across function activations. Full eager emission stays the default.
