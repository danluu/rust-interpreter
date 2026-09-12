# Preserved isolated candidate failure

Debug library tests reached 149 passes, two failures and one ignored. Integration
and release tests did not execute. The medium-copy test expected rejection by the
old block-local heuristic; it now admits the proven cross-block leaf. Add execution
checks for that newly admitted form while retaining all original cold-branch,
alias and exact-budget checks.

The new nested-fault test assumed native and interpreted memory diagnostics use
the same text. The retained JIT deliberately returns its established generic
memory-fault string, as covered by existing tests; this is not new candidate
behavior. Correct the new test to recognize only that existing spelling when the
interpreter reports this fixture's exact invalid-memory error, retaining equality
of every instruction-limit failure and the budget where the memory fault occurs.
No benchmark assertions or runtime diagnostics are changed. Both failures and the
exact isolated source/recipes/logs remain. No tool was published.
