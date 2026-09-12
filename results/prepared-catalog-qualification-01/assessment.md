# Selected test catalogs survive optimized roots

The exporter now preserves selected function identities in a catalog bound to
its exact bytecode, target and entry. The VM validates that catalog before any
guest execution or suite report creation. Optimizing the batch root no longer
breaks isolated execution; the actual Ruff export now runs all six selected tests.
Ordinary bytecode execution and the wire format remain compatible.

Qualification passes 322 Rust tests in each profile (one ignored), 40 Python
tests, and 68 real fixture/project commands: 16 fixture, 32 pgrust edit/check/
restoration, 12 Ruff and eight fre. Tests cover Result adapters, optimized roots,
malformed/stale catalogs, wrong-edit failures and strict rejection of an unused
borrow error. Each pgrust bytecode snapshot retains its catalog and verifies
executed names/function IDs. Ruff and fre use matching retained native oracles
and fresh actual exports; replayed guest entropy gives exact isolated comparisons.

The first fre controller omitted the established 150,000-allocation limit,
causing a trap at the default 100,000. Older/newer diagnostic controls reproduced
that incorrectly limited run. This did not prove a lowering defect. Correcting
the limit passes the actual recompile/run and exact replay with unchanged
bytecode. Both the failed run and the correction are preserved. Two folded
setups and storage admissions stopped before workload commands and are also
recorded. No performance claim follows from these correctness qualifications.

The optional isolated runner still has separate guest state per test and does
not implement libtest ignore, should-panic, unwind or thread semantics. Next
expose effective limits and compiler-derived test discovery.

[Qualification receipts](summary.json) ·
[Fre correction](../prepared-catalog-token-corrected-02/summary.json)
