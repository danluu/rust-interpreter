# Demand-only incremental query value retention

`scripts/interpreter.py --query-cache-retention demand` is an experimental,
default-off cache retention policy. It changes no application source or
manifest, and retains ordinary Rust analysis, borrow checking, lints, metadata,
native host builds and compiler finalization. Performance qualification is
separate; this prototype does not establish a sub-0.5-second edited build.

Rustc's incremental graph can validate a query without needing its return
value. At finalization, the pinned compiler loads every such green disk-cached
value just to serialize it again. This policy omits that promotion pass and
serializes values actually computed or loaded by the current compilation.
Tracked diagnostics and feature-use side effects are still serialized.

An evicted value can subsequently be demanded. The normal query engine then
recomputes it using the original provider and compares its result fingerprint
with the previous fingerprint. The policy does not mark additional nodes green,
change query dependencies, or accept unchecked results. Eviction can make later
compilations slower, so performance comparisons must include long edit histories,
newly reachable functions and changing dependencies, including all cache writes.

## Isolation and supported configurations

Before creating the compiler context, the driver appends
`.rust-interp-query-demand-v1` to the configured incremental directory. Stock
and demand-only cache histories are therefore physically separate even when a
direct compiler caller switches modes with the same `-Cincremental` argument.
The launcher also separates Cargo workspace identities, preventing a fresh
Cargo unit from suppressing newly requested callbacks. Off mode preserves the
existing directory and routing.

This isolation is required for correctness. Stock finalization assumes that a
green cacheable query has a persisted value and reports an internal error if
one is absent. It must never promote values from a demand-only cache.

Disabled incrementality, dependency-graph dumps/assertions, full incremental
hash verification, a forced compiler cache version, alternate codegen backends
and unreviewed provider overrides select the ordinary path before the context
and cache directory are created. A detected unexpected save hook is an adapter
invariant failure before analysis, not permission to run stock finalization
inside the demand-only namespace. The reviewed borrow-check cache override can
be composed with this option. Partial analysis mode is rejected.

Cache directories are internal implementation state. Do not manually pass a
nested demand-only directory as a stock compiler's incremental directory.

## Serialization and publication

The driver preserves the pinned `RSIC` header and uses stock
`OnDiskCache::serialize` for the entire value, allocation, hygiene, source-file
and diagnostic format. It changes neither rustc's version nor stable crate IDs.
The header uses the compiler's exact `Session::cfg_version`; forced version
overrides are declined before choosing the demand-only namespace.

Serialization itself has a relevant late query: encoding a static allocation
asks `codegen_fn_attrs` whether it is thread-local. Without full promotion, that
value may not be resident. The previous cache mmap therefore stays alive while
the new cache is written to a separate temporary inode. If the serializer starts
query jobs or changes side-effect, feature-use or source-file inventories, that
attempt is discarded and serialization repeats. Only a pass over stable state
can be published. All attempts are counted and belong to build time. Failure to
stabilize within 16 passes reports a tool error without committing a successful
cache session.

This depends on the **pinned encoder's phase ordering**, not merely counter
equality. Query-value encoders hold cache shard locks while structurally encoding
values and queuing allocation IDs. The TLS-attribute query happens in the later
allocation loop, after query-cache and side-effect iteration locks are released.
Newly materialized attributes, diagnostic records and imported source files are
included in the next pass. Queries are memoized within the compiler session, so
these passes reach a fixed point for the reviewed encoders. A future reentrant
encoder could deadlock before any counter is checked; a toolchain update requires
reviewing this ordering again.

After stable serialization, the driver closes the old mmap, unlinks the inherited
query-cache hard link and renames the completed temporary file into place. It
never truncates a prior successful session's inode. Dependency-graph staging,
query-key verification and graph encoder completion retain ordinary ordering.
The standard compiler still decides whether to finalize the working incremental
directory. Existing errors skip saving; serialization errors abort; a failed
dependency-graph rename reports an error, preventing successful finalization.
Adapter I/O errors have explicit adapter diagnostics rather than copied private
rustc diagnostic types.

## Correctness checks and observations

`tests/test_demand_retention.py` runs only when `RUST_INTERP_TEST_EXPORTER` names
the candidate exporter. It covers repeated edits, newly reachable ordinary and
generic functions, opaque results, stock/demand/off transitions, unsupported
configuration fallback, warnings and lint expectations, uncalled type/borrow
errors and restoration, retained hard-link contents, foreign statics, thread-local
statics, linker attributes, and exact selected bytecode versus stock export.
`RUST_INTERP_TEST_VM` enables execution of those selected artifacts alongside
ordinary native tests. The caller must hold the shared repository benchmark lock.
`tests/test_demand_retention_cargo.py` adds actual Cargo host build scripts,
shared host/target dependencies, body and dependency edits, selected library and
test exports, byte parity with off mode, native execution and failure restoration.

Rust routing/header tests and `tests/test_demand_retention_launcher.py` cover
mode parsing, compiler probes, Cargo-only environment propagation, immutable tool
capabilities, namespace separation and refusal to execute after failed checking.

`rust-interp-query-cache-retention:` reports the requested mode, actual cache
directory, bypass reason, omitted promotion passes, serialization attempts,
serializer-started query jobs, final cache size and retained side-effect count.
These are counts, not measured savings or skipped validation. Cargo may replay a
fresh unit's saved stderr; repeated reports do not identify new compilations.

The September 13, 2026 local correctness run passed 94 Rust tests, 7 retention
launcher tests, 6 direct compiler histories, 1 Cargo history and 18 existing
borrow-check compatibility tests. The exporter was a debug build with debug
information and tool-build incrementality disabled; fixture incrementality was
explicitly enabled. The supplied VM executed both library and selected-test
exports, and ordinary native controls checked current outputs. All successful
retention saves in these fixtures used one serialization pass and started zero
serializer query jobs. Thus the repeated-pass branch has source review but no
positive runtime regression case yet. The private run receipt is
`.work/demand-retention-correctness-03/receipt.json`; this correctness run supplies
no performance qualification.

## Pinned compiler references

These paths are under the `nightly-2026-09-08` `rustc-dev` source tree, rustc
revision `cea272fa356e94bd2ee2cadf376630aa0683867a`:

- `rustc_incremental/src/persist/save.rs`: promotion and cache persistence.
- `rustc_incremental/src/persist/file_format.rs`: exact header and I/O contract.
- `rustc_incremental/src/persist/fs.rs`: directory layout, inherited hard links,
  and successful-session finalization.
- `rustc_query_impl/src/incremental.rs`: stock promotion's missing-value invariant.
- `rustc_query_impl/src/execution.rs`: missing-value recomputation, fingerprint
  verification and query job creation.
- `rustc_middle/src/query/on_disk_cache.rs`: stock serialization phases.
- `rustc_middle/src/query/caches.rs`: shard locks and iteration quiescence.
- `rustc_middle/src/mir/interpret/mod.rs`: static allocation TLS-attribute query.
- `rustc_middle/src/ty/context.rs`: `TyCtxt::finish` ordering.
- `rustc_incremental/src/assert_dep_graph.rs` and `persist/clean.rs`: diagnostic
  routines are no-ops for the configurations admitted by this adapter.
