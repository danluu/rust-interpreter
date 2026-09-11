# Native-call eligibility census

This diagnostic compiles the actual JIT support predicate/local-fill proof and
reads typed bytecode with an exact matching saved profile. It does not execute
guest code. Function IDs and whole recorded operations establish correspondence;
display names and parsed Debug operands do not determine eligibility.

After the active benchmark cohort finishes, run from the repository root:

```sh
python3 benchmarks/experiments/native-call-census/run.py --run-id native-call-census-01
```

The runner takes the benchmark lock, verifies the emitter predicate is unchanged
from the profile's source commit, freezes inputs, builds offline in a fresh target,
runs diagnostic tests, and cross-checks instruction/call totals against the prior
independent frame census. Full per-callee output stays in `.work`; the public
report contains hashes, aggregate counts and leading included/excluded callees.

Leaf eligibility allows a proposed native Return operation. Acyclic leaves also
have a conservative whole-body virtual-instruction bound for a budget preflight.
A separate direct-call closure measures a broader structural upper bound,
including recursive cycles. Explicitly prospective groups additionally require
native terminal-Trap handling; another bound excludes loops and recursive calls
and charges every static call site, including repeated calls to the same target.
Neither proves an ABI, trap/budget continuation, native region capacity or a
performance gain. Calls/bytes/instructions are different quantities from time.
