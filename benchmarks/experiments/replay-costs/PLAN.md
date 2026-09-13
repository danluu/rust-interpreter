# Observe current function-cache binding costs

Start from adopted main56dcd32 with complete-tool baseline e729a493. The token
edited-command median has124ms prior-template binding inside612ms lowering.
The custom VM remains the dominant3.077s stage. This is a bounded exporter
diagnostic, not a performance candidate or a cache-format implementation.

Add optional RUST_INTERP_REPLAY_COSTS=0/1, recorded in compiler environment
dep-info. Reject other values and require actual reuse plus strict checking
when enabled. Record aggregate counts and three coarse intervals inside actual
template reuse: setup/current-MIR lookup/Imm indexing; replayed events and
current-session resolution; Call/frame-observation patching. Keep temporary
destruction and timing bookkeeping visible as enclosing binding minus summed
phases. No per-event clocks or per-function JSON. Counts must reconcile with
reused functions. No program transformation, relaxed check or cache-format
change. Verification replay continues without the observer.

Build only the exporter package, with its75 existing tests in debug and
release, and its release binary. Preserve the exact qualified VM/wrapper from
e729a493 rather than rebuilding or repeating their unchanged profile tests.
Keep source committed/frozen, two Cargo workers, the existing owned host target,
45-second shared-lock admission and8GiB floor. No concurrent own build/profile.

Before collecting real costs, qualify observer off/on bytecode and catalog
identity through a complete production source history. Use an owned launcher
adapter to set the option only inside the Cargo-check child; ambient launcher
variables are sanitized. Test absent/0/1/invalid values, auto-without-reuse and
strict errors. Check cold zero-reuse counts, warm actual reuse, changed-source
and wrong-edit assertions, restored source, cache miss/hit and option-dependent
Cargo invalidation. Use fresh namespaces and explicit guest flags/limits from
the completed token comparison. Do not mutate its retained caches.

The selected project diagnostic uses the current12-test token history and
first-cycle reference artifacts, preserving the allocation-history constraint.
Initially require12GiB plus the8GiB per-command floor. Report observer costs
only after parity passes, with baseline counters and residual accounting.
The flag may perturb execution; no timing adoption verdict follows. Choose
a subsequent optimization from measured phase costs, not25,442 historical
event counts or assumed hash-lookup costs.
