# Keep private pointer values out of local memory

Current real-suite profiles show substantial logical Local/Copy/Load/Store work
in generic code and Rust's precondition checks. The exporter already promotes
private primitive local slots to bytecode registers, but its type filter excludes
raw pointers. Investigate extending that existing proof to private raw-pointer
values. This is a generic compiler transformation, with no project/function-name
special cases and no changes to the guest pointer representation or call ABI.

First inspect the exact typed-use and final-bytecode address proofs. A pointer
value and the storage holding that pointer are distinct: dereferencing the value
does not itself expose its local slot. Taking the address of the slot does.
Keep function arguments/results, call operands/destinations, aggregates, borrows,
address exposure, ambiguous overlapping colored ranges and unknown uses excluded.
The existing final-bytecode proof must still accept only full-width accesses via
unique, dominated Local addresses; never use sampled values as an alias proof.
Start with thin raw pointers of the pinned 64-bit guest ABI. Do not admit fat
pointers, references or function pointers in the first candidate.

Preserve old promotion opportunities and bounded work. Adding pointer candidates
must not cause a function that previously fit the 256-slot bound to lose all its
integer/float promotions. Retain legacy candidates first, admit only remaining
new capacity, and report both categories. No new bytecode opcode/version or VM
change is required. Logical budgets continue to count each resulting artifact.

Qualify typed Rust fixtures for dereference, pointer arithmetic, branches, loops,
stores through pointers, address-exposed pointer slots, calls, aliases and strict
unused type/borrow errors. Compare both interpreters/JITs against native assertions,
preserve faults at remaining guest memory accesses, and verify unchanged excluded
functions. Run workspace tests in both profiles and real exports before timing.

Use an early actual source-edit/build/test screen with native, retained and
candidate controls, unchanged profiles/workers/limits and original assertions.
Require at least 10% paired token wall improvement with no CPU regression and
separate folded/pgrust regression guards before broad qualification. Predeclare
the exact edits/order/identities before execution. Failed screens stop without
retiming; do not reopen the parked scalar call ABI, whole-call inliner, clearing,
function-cache, rematerialization or register-cache experiments.

One workload at a time, global lock with a 45-second wait, two Cargo workers and
8 GiB free before children. Preserve raw evidence, sources, installed tools,
private caches and unrelated work. This remains a feasibility investigation until
the typed proof and real exports establish useful coverage.
