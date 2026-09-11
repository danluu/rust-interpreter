# Allocation trace preserves fixture bytecode and execution

All 383 recorded commands pass with the original four fixtures and assertions.
For each fixture, old-tool, new-tool trace-disabled and trace-enabled exports
are byte-identical. Thirteen inputs execute in fresh native processes and in
both custom engines for all three artifacts: 52 native and 312 custom runs.
The remaining commands are four native compilations, twelve exports and three
intentional configuration rejections. No performance conclusion is drawn.

| Original fixture | Trace events | Relocations | Cache hits | TLS identities | Partially initialized allocations |
| --- | ---: | ---: | ---: | ---: | ---: |
| scalar_constant | 174 | 5 | 17 | 0 | 0 |
| static | 369 | 13 | 36 | 0 | 2 |
| tls | 1845 | 122 | 125 | 9 | 23 |
| caller | 147 | 13 | 11 | 0 | 1 |

The trace verifier checks ordered event IDs, parent/request/resolution edges,
allocation caching and cyclic static identities, alignment and initialization
masks, original relocation bytes, and the final artifact-hash footer. Invalid
trace values, partial-checking and audit combinations reject with status 2 and
remove stale standalone bytecode/trace outputs. All twelve source/input hashes,
immutable tool binaries and the raw command ledger hash verify. Supervisor
3477/controller 3481 finished successfully.

This qualifies the diagnostic on these fixtures. It does not yet explain the
Nushell cross-history layout difference or establish stable cache identities.
The launcher is unchanged while the worker study keeps its inputs frozen. A
large original/wrong/API/revert trace remains next after that study closes.

See [summary](summary.json), [release](../allocation-trace-release-01/assessment.md)
and [design](../../benchmarks/experiments/artifact-diff/CONSTANT-IDENTITY-NEXT.md).
