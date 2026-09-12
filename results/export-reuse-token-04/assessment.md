# Token binding reconstruction passes

All eight production states preserve the retained bytecode exactly and pass the
original expected assertion outcomes, including the wrong edit and restoration.
Every original function is fully lowered. The second exporter graph reconstructs
5,203 functions from encoded/decoded owned instructions, frame observations
and current-MIR binding recipes; 172 unsupported recipes use full lowering.
Scheduling, guest bytes, addresses, alias classes, TLS and diagnostics match.

The original-state payload is 60.98 MB. The measured diagnostic interval
includes serialization, reconstruction and repeated whole-graph comparisons; it
is not a cache lookup time or performance result. No persistent payload was
loaded and no original lowering was skipped.

The initial scalar-constant check stopped because the verifier required numeric
compiler allocation IDs to match. Rustc's caller-location hook creates fresh
IDs on repeated calls. Guest bytes and addresses agreed. The corrected check
preserves the address of every shared ID and each address alias class's
cardinality; it never merges allocations by contents. A dedicated unit test
rejects changed shared addresses and merged/split alias classes. The repaired
source passes 47 exporter tests in both profiles, 231 complex-fixture commands,
and 229 semantic-edit commands before this production history.

Proceed to prior-session payload verification using the compiler's incremental
session transaction. Then measure actual skipped work and complete edited
build/test commands. [Summary and frozen evidence](summary.json).

Matching snapshots in this history hard-link the frozen retained reference
only after the actual executed artifact hashes identically. Any differing
output would be copied before the history stops. No prior snapshot is changed.
