# Warm reuse misses on the real token edit history

The opt-in observer passes83 exporter tests per profile,14 Python tests,
28 Cargo fixture commands and16 fre commands. Observer off/on produces the
same bytecode, entry catalogs and twelve original test outcomes as the retained
reference, including the deliberately wrong edit. Uncalled type and borrow
errors still stop before execution. The first fixture attempt stopped after26
commands because its driver expected the wrong diagnostic for the launcher's
unsupported `verify` option; that failure remains recorded separately.

Across the five valid edits,172 functions are green but have no saved template.
Every one declines again with first reason `binding has no current MIR recipe`.
Only34,33,32,1 and30 functions respectively have a red dependency node and a
prior template. All of those are lowered and staged successfully. No valid
edit has a red function without a prior template. Thus the familiar204 lowered
functions in edit3 comprise172 recurring unsupported recipes and32 red entries;
they are not204 bodies invalidated by the source edit.

| Diagnostic, median of five edited exports | Result |
| --- | ---: |
| Reused functions | 5,218 |
| Preparation plus lowering, all missed functions | 31.88ms |
| Preparation plus lowering, declined recipes | 22.88ms |
| Preparation plus lowering, other misses | 8.99ms |
| Reused-template decoding | 40.37ms |
| Binding | 144.28ms |
| Current-MIR context within binding | 106.19ms |
| Reused recipes that require no MIR body | 804 |
| Context within those body-free recipes | 4.55ms |

Combined costs are summed inside each observation before taking medians.
Other rows are independent medians and need not add. These are perturbed
diagnostic intervals, not end-to-end speed measurements. The4.55ms body-free
context is only an upper bound on a lazy-MIR saving: it includes template
unpacking, and moving required MIR work into event processing saves nothing.
The remaining context belongs to recipes that do use the current body.

Park both a standalone lazy-MIR change and a broad template-recipe expansion
as immediate optimization candidates. Their measured cost bounds are small
relative to the compute-heavy token execution gap. Keep the observer for
future frontend investigations. Prioritize a new runtime composition informed
by the qualified Copy and budget samples; retain the scalar-copy campaign's
failed full adoption verdict, and declare fresh gates before any new timings.

This report identifies cache state and the first unsupported recipe reason.
It does not reconstruct individual rustc dependency edges or prove a specific
source-level cause of each red node. Full function rows remain in the local raw
records; the published diagnostic summary is bounded.

[Build identity](../reuse-misses-build-01/summary.json),
[fixture](../reuse-misses-fixture-02/summary.json),
[real history](../reuse-misses-token-01/summary.json),
[44-command qualification](../reuse-misses-validation-02/summary.json),
[retained harness failure](../reuse-misses-fixture-01-failure/summary.json),
[five-edit reconciliation](summary.json).
