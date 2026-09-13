# Reuse of successful empty borrow-check results

The optional `--borrowck-cache verify|reuse` launcher setting targets a result
reconstruction cost in the pinned rustc frontend. It requires no application
source or manifest changes. It is disabled by default, and no performance
improvement or sub-500 ms Nushell build is established by its correctness tests.

This is a narrow optimization. Rustc already reloads unchanged optimized MIR
in ordinary edited builds, avoiding the borrow-check provider altogether. The
first correctness run found zero opportunities in those cases. Additional
fixtures cover functions becoming reachable and changes to inlined callees:
these can demand an unchanged borrow-check result without a reusable enclosing
MIR result. Avoided provider calls are not evidence of lower total build time.

The [correctness qualification](../results/borrowck-query-reuse-01/assessment.md)
passes 146 tests across exporter/routing, launcher, direct compiler and Cargo
scopes. Each positive reuse fixture avoids three provider executions while
retaining the original provider for its nonempty opaque result. The pinned
compiler defaults to Polonius-next; the nondefault bypass fixture uses legacy
Polonius.

Rustc's `mir_borrowck` query returns a result containing a map of inferred opaque
types. Most ordinary function bodies return a successful empty map. This query
has no on-disk result cache in the pinned compiler. Although ordinary analysis
can validate an unchanged query without obtaining its value, later MIR work can
request that value and cause the original provider to run again.

The new provider handles exactly one reconstructible value: `Ok(empty map)`.
It requires rustc to have already marked the actual `mir_borrowck` dependency
node green, meaning rustc validated its recorded inputs and replayed tracked
diagnostic side effects. It then computes the query's own fingerprint for an
empty successful value and compares it with that node's previous result
fingerprint. Only a match permits reconstruction in the current compiler arena.
The normal query engine also performs its existing fingerprint consistency
check. Both checks rely on rustc's ordinary incremental fingerprint assumptions;
they are not independent protection against collisions.

There is no new persistent sidecar, pointer serialization, public-API hash or
claim that an unchanged function signature proves reuse. The previous query
graph is the sole certificate, including across off/on mode transitions and
failed compilations. Nonempty opaque results, errors, red or unknown nodes and
unsupported configurations use the original provider. `verify` always invokes
the original provider and checks that every proposed hit actually returns an
empty successful map; `reuse` reconstructs qualified hits.

All aggregate analysis, type checking, required borrow checks, lints, lint
expectations, native host compilation and compiler finalization remain in
place. MIR dump/fact/validation requests, nondefault borrow-checker configuration,
internal compiler attributes, disabled incrementality, existing compiler errors
and unreviewed provider overrides decline the optimization. Native compilation
through the adapter requires the pinned toolchain's actual rustc executable.

## Use and evidence

Add `--borrowck-cache verify` or `--borrowck-cache reuse` to an existing
`scripts/interpreter.py` command. Enabled modes have separate Cargo workspace
identities; omitting the option retains the previous identity and compiler
routing. The installed tool must advertise the `borrowck-cache` capability.
The setting applies to the selected exporter and ordinary dependent compiler
units; it does not prune the Cargo graph or remove the application's test
harness dependencies.

Each participating compiler process prints `rust-interp-borrowck-cache:` followed
by JSON counts: original provider calls, green candidates, matching/mismatching
result fingerprints, verified proposals, reconstructed results and any bypass
reason. `provider_wrapped` distinguishes an active observer from a configuration
that uses the standard compiler directly; bypassed calls are not counted.
These counts describe avoided provider executions, not saved time.
Reports identify the process and crate/test unit. Cargo can replay a fresh
unit's cached stderr, including an old report; repeated lines are not evidence
of a new compiler invocation and must not be summed across Cargo commands.

Enabling the option also routes ordinary dependent compiler invocations through
the exporter, which can add startup overhead. Native compilation retains the
public rustc logger, ICE/Ctrl-C handlers, native configuration callback and
`-Ztime-passes` total reporting. Rustc's private fatal-signal diagnostic hook is
not exposed to custom drivers. Normal off-mode routing is unchanged.

The opt-in correctness suites are `tests/test_borrowck_cache.py` and
`tests/test_borrowck_cache_cargo.py`. Set
`RUST_INTERP_TEST_EXPORTER` to the newly built exporter; optionally set
`RUST_INTERP_TEST_VM` and `RUST_INTERP_TEST_ARTIFACT_DIR` to execute exported
programs and retain exact commands and diagnostics. Run it while holding the
repository's shared benchmark lock, including when using an isolated worktree.
It compares native results and diagnostics after real fixture edits, with
borrow/type failures, opaque types, warnings and expectations, mode changes,
disabled incrementality and dependency invalidation. It is a correctness suite,
not a performance benchmark.

## Scope relative to Nushell

The retained Nushell timings show 19 compiled/checked units after edits and
seconds of Cargo/frontend work, with only about 40 ms in selected bytecode
export. The particular retained 19-unit runs use ordinary incremental MIR
settings, which disable normal MIR inlining. A separate correctness fixture
uses explicit MIR level 3, a supported launcher setting that enables inlining;
that fixture does not establish a gain for those Nushell runs.

This change targets work inside compiler processes. It does not
eliminate Cargo's downstream invocations, macro expansion, native build scripts
or all query recomputation. Further compiler-level reuse remains necessary to
approach the proposed 0.5 s complete warm-build target. The user clarified that
the restriction on new benchmarks applied only to the initial report. The
[active optimization protocol](../benchmarks/experiments/strict-warm-build/PROTOCOL.md)
allows benchmarking; performance qualification of this feature remains open.

In particular, a wrapper cannot safely suppress downstream compilation using
only a public-signature hash: exported generics, constants, macros, trait
implementations and opaque types can change the facts a consumer uses. This
implementation leaves Cargo invalidation intact and uses rustc's tracked
semantic dependencies. Persisting broader frontend state and changing
cross-crate metadata invalidation remain separate compiler integration work.

The [retained Nushell interval audit](../results/cargo-residual-nushell-01/assessment.md)
places most elapsed time inside reported compilation-unit intervals; its
uncovered time remains unattributed. This implementation does not establish
which part of that historical work it can avoid.

## Pinned compiler review references

Paths below are relative to the `nightly-2026-09-08` rustc source tree supplied
by `rustc-dev`, under `lib/rustlib/rustc-src/rust/compiler`:

- `rustc_middle/src/queries.rs`: declaration and exact result of `mir_borrowck`.
- `rustc_query_impl/src/execution.rs`: `load_from_disk_or_invoke_provider_green`
  reruns uncached providers and checks reconstructed result fingerprints.
- `rustc_middle/src/dep_graph/graph.rs`: green-node proof, previous result
  fingerprints and replay of `QuerySideEffect::Diagnostic` / `CheckFeature`.
- `rustc_borrowck/src/lib.rs` and `root_cx.rs`: normal provider uses local
  borrow-checking state and returns its hidden-type map or an error.
- `rustc_borrowck/src/nll.rs` and `polonius/dump.rs`: requested diagnostic files
  require executing the original provider.
- `rustc_interface/src/passes.rs`: complete `analysis` stays unchanged.
