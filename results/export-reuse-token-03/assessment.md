# Compiler dependency observation supports a token reuse experiment

The pinned compiler marked 5,350–5,374 of 5,375 functions green during the
five production edits. Every function was nevertheless fully lowered. All
green typed templates matched the preceding successful export, with no unknown
green keys. All eight bytecode artifacts and original assertion outcomes match
the retained exporter, including the wrong edit and the actual restored-source
rebuild.

Using the earlier unannotated function weights, supported green functions cover
median **443.93 ms (96.47%)** of function work. The green checks take median
**21.83 ms**; that timer excludes construction of the mono-item dependency key.
These are instrumented diagnostic intervals, not performance samples or a
measured end-to-end improvement. No work was skipped.

The implementation requires strict checking and an incremental dependency graph.
It tracks frontend query reads with a concrete mono-item node; a green node
retains its old edges while full verification runs without creating a duplicate
node. The 229-command body/layout/constant/signature/generic fixture and the
179-command complex fixture checks precede this history.

Proceed to current-session binding recipes and actual reuse. A payload needs
owned instructions, frame-packing observations and an ordered description of
graph interactions. Constants must be reevaluated from current MIR, preserving
compiler allocation identity and aliases; function references and TLS/caller
addresses must be rebound. The observed template hash alone is not a safe key.

Exact commands, source/artifact/census hashes and frozen inputs are linked from
[the summary](summary.json). Raw evidence remains local under
`.work/export-reuse-token-03`; completed regenerable Cargo metadata was retired
with all evidence verified in `.work/export-reuse-space-02/summary.json`.
