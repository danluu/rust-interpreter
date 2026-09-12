# Exact profiles of the current suite's dominant tests

Catalog-selected profiling passes 340 Rust tests in debug and release (one
ignored). The fixture proves the selected test runs while the root and unselected
test do not; it also checks stale catalogs, unknown names, conflicting options,
existing outputs and guest failures. The initial test command incorrectly passed
JIT-only flags to the interpreter control; the VM rejected them as intended.
The corrected fixture passes without changing the VM implementation.

All fourteen real VM commands pass: seven fresh single-test controls on retained
VM `40cca8a7`, each followed by exact-entropy profiling on `c013f239`. They cover
both dominant tests in the current twelve-test token artifact, the dominant
eighteen-test folded artifact entry and all four pgrust hashfn tests. Every pair
has identical logical instruction counts and guest memory peaks; all native test
outcomes match, both recorded entropy counters match, and no JIT function declines.
Saved artifacts and full catalogs remain unchanged.

| Selected test | Logical instructions | Native regions, excluding single Call/Return | Mean region length |
| --- | ---: | ---: | ---: |
| Token block boundaries | 15,570,943,472 | 534,974,241 | 28.77 |
| Token exhaustive | 12,862,074,426 | 693,355,479 | 18.23 |
| Folded short-string/window comparison | 4,109,988,334 | 158,797,515 | 25.56 |

The added token test spends much of its logical work in regex determinization;
the old exhaustive test has different hot functions. Copy precondition checking
accounts for 1.75 billion native bytecode operations in the latter, plus 683
million in its nonoverlap helper. These are execution counts, not sampled machine
time or estimates of removable work. All checks remain enabled.

The pinned Rust library's `core/src/ub_checks.rs` explains a relevant backend
obligation: precondition checks deliberately resist MIR inlining and rely on
later backend optimization. Our exporter correctly uses the session's UB-check
setting; it does not simply enable those checks unconditionally. The current
private-local promoter already handles integers, floats, bools and chars, but
excludes pointers. Investigate whether private pointer **values** can use the
same representation without changing their pointees, the call ABI, or checking
behavior. Preserve address-exposure exclusions and existing promotion budgets.

The new `--profile-test` path starts a fresh JIT for each command. These results
are not prepared-suite timings or source-edit/build/test measurements. The
existing profile schema stays intact; stderr records exact artifact/catalog
digests, selected function/name and original root. Failed guest executions still
produce no complete profile. Full names, operations and counters stay in local
profiles; the committed report bounds displayed function-name prefixes.

[Report](summary.json) · [Build](../suite-profiling-build-02/summary.json) ·
[Plan](../../benchmarks/experiments/suite-profiling/PLAN.md)
