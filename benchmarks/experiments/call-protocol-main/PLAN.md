# Main/compiler integration qualification

Merge main7744629 into the call-protocol branch after its token result failed
adoption. This is correctness qualification of a new source integration, not a
retry of the unchanged failed performance candidate and not default adoption.
The active token/folded/pgrust measurements keep immutable8f1070db binaries;
all their frozen inputs remain unchanged by this source integration.

Main reduces repeated compiler analysis and moves owned leaf-inlining data.
The experimental source has broader CFG initialization proofs and bounded
one-call expansion. Resolve three source conflicts by retaining both behaviors:
make selection against the original graph, install owned replacements only
after all decisions, retain the broader proof and exact growth/diagnostic
rollback. The borrowed and owned transforms are compared on all existing
semantic fixtures. Adapt the two ownership fixtures whose old assumptions
changed: a two-call original node remains ineligible for whole-call expansion;
a valid caller crossing the CFG proof's register bound exercises conservative
rejection and budget rollback. No runtime/source assertion is weakened.

Host qualification floor: 4 GiB. Use the existing qualified host dependency
cache, two Cargo workers, locked offline dependencies and the shared benchmark
lock with45-second admission. Run418 Rust tests in each of debug and release,
one ignored per profile. Build and install the current exporter, wrapper and
custom VM from a frozen committed source tree. Preserve every failed attempt;
fix concrete failures before restarting qualification under a new run ID.

Run the Python harness checks, exact original saved selections, serial/replayed
and ordinary two-worker suites, and203 strict native/cache commands with the
new immutable tool identity. Type/borrow errors still stop before execution;
new cache namespaces bind to the rebuilt compiler. Equivalent bytecode must
retain instructions, memory and test outcomes. This qualification alone makes
no performance claim. Further runtime work will use the counter diagnostic
and complete changed-source costs; no automatic performance retiming is queued.
The independently planned Nushell native calibration follows qualification.
