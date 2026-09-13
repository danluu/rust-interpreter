Both original ignored compiler controls pass with the stock pinned compiler,
the newly tested exporter and the exact measured guarded-local-facts VM. All
130 internal compiler/native/VM commands have retained terminal receipts.

The four path-remapping scopes preserve native file/caller/panic observables,
both fast and projected-store panic lowering paths, and exact bytecode identity
where the original controls require it. Uncalled type, borrow and const errors
retain full unnormalized native diagnostics; restored source executes correctly.
The test harness explicitly uses two stock codegen units. Its guest fixture and
assertions are unchanged.

The first controller admission refused before executing any test because it
expected the older Cargo executable directory. Its receipt is retained. The
revised controller binds the exact successful test executable in this pinned
Cargo's package/hash/out layout. No successful control command was repeated.
These are compatibility results, not timing evidence.
