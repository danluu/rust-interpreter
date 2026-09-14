# Private aggregate native ABI qualified; production selection remains narrow

All six native controls pass in debug/release. The complete bytecode library also
passes in both profiles: 367 passed, 16 existing diagnostics ignored. The four
commands, exact source and logs are closed at d0a836a1.

The custom emitter executes each original body once and writes a private payload
of up to 64 bytes. Shared field offsets also update legacy native Calls. Controls
cover all result widths, 468 independent overlapping-copy cases, unequal and
nonmonotonic paths, all short budgets, eight profile words, private faults,
64 arguments, 1 KiB frames, host-register/SP preservation and output canaries.
Wide bodies still require the explicit test entry; production eligibility has
not changed.

Proceed to the complete Call bridge, with a single destination precheck and
ordered commit of all logical result bytes. Full success/error memory snapshots
and fallback ordering remain required before workspace, strict/cache and original
profile qualification. No original-project timing or runtime adoption follows
from these synthetic controls.
[Summary](summary.json), [closure](closure.json),
[prospective timing policy](../../benchmarks/experiments/scalar-aggregate-model/NATIVE-NEXT.md).
