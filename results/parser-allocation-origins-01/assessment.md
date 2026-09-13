# Restored parser constants already differ in the compiler

The extra string storage originates before exporter layout. With function-template
reuse disabled, all five references to the exact 12-byte `syntax error` allocation
share one compiler allocation in the original and wrong-edit states. After the
parser refactor, `parse::Parser::yyparse` references one allocation while
`reduce_cold` and `range_var_from_qualified_name` reference another. Source
restoration retains that split. Compiler IDs are compared only within an export.

| Diagnostic state | Exact initialized literal allocations | Request groups |
| --- | ---: | --- |
| Original | 1 | All five requests share one ID |
| Wrong initial lookahead | 1 | All five requests share one ID |
| Cumulative parser refactor | 2 | Two yyparse requests / three action requests |
| Restored original | 2 | Same split into parser / action requests |

These are immutable allocations with alignment1, reserved at16-byte boundaries
by the existing exporter. Equal contents do not make the two compiler identities
interchangeable. No deduplication or pointer normalization is applied.

The eight diagnostic commands use two independent incremental Cargo histories,
both with function-template reuse off. The allocation observer is enabled in
only one history. All114 original outcomes match the retained native controls;
observer-off/on bytecode and catalogs match at all four states. Sources restore.
The original artifact is exactly `903925ce` and the restored artifact exactly
`d1cc2e55`, reproducing the stopped performance history with template reuse off.
The observer therefore does not introduce the difference, and function-template
reuse is not required for it.

The typed decoder reports32 additional readonly bytes, unchanged function
headers/opcode kinds,9,121 changed immediate operations in2,650 functions and
one changed static-initializer byte. The trace establishes the literal split;
it does not classify every changed immediate or prove whole-program equivalence.
This is consistent with the earlier traced mixed decoded/recomputed MIR behavior
in [Nushell](../allocation-history-mir-dumps-02/assessment.md).

Preserve the original incremental benchmark's cross-cycle identity failure.
A revised comparison should keep byte identity between custom A/B at matching
source and compiler-history positions, preserve all native assertion controls,
and explicitly record cross-cycle artifact histories. Do not alter the engine
to force identities to merge. Retaining the22 valid completed commands and
running44 unstarted commands avoids selecting or repeating timing observations.
The revised protocol needs separate qualification and a separate result identity.
