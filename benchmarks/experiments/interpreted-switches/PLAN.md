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

Implementation: independent branch from adopted runtime main (7d47e595), with
explicit --indexed-switches, disabled by default and requiring full validation.
Construct indices only when a >=32-case Switch is interpreted. Dense spans of
at most four times the case count use relative slots; other inputs use sorted
original positions with key/position tie order. All arithmetic uses u128 until
a bounded range proves conversion safe. Missing keys use the original default.

One fresh cache per invocation borrows the immutable Program and keys entries
by function/PC. Cap 256 entries, 65,536 cases per index and 1 MiB of retained
vector allocation payload. Allocation/budget refusals retain linear lookup;
cached refusals avoid repeated construction. No preparation scan, bytecode
rewrite, native emission, frame clearing or compiler change. Four Rust controls
cover independent lookup oracles, bounds, budgets, profiling, full validation,
and repeated/alternate prepared execution; one launcher control covers routing.
