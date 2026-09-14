# Large interpreted switch census

Before a runtime change, inspect exact adopted token block/exhaustive, folded
and parser profiles. Parse only complete numeric Switch renderings, retaining
original case order and targets. Report large (at least 32-case) switches,
ascending/contiguous/duplicate properties and interpreted execution counts.
The product cases * executions is only a worst-case linear comparison bound.
No guest value distribution or time savings is inferred. Bind profile closures
and source, shared lock, 8 GiB floor, zero new guest executions.

A candidate may use bounded immutable lookup metadata and exact u128 comparisons
if evidence supports it. Preserve first matching duplicate, default targets,
budget/fault ordering, profiling and prepared-owner isolation. Do not rewrite
guest bytecode or relax checking. Any candidate requires independent controls,
strict Cargo qualification and changed-source primary/held-out gates.
