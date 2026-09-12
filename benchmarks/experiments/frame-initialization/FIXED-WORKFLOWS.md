# Fixed-clearing library comparison execution

Use the nine cases and per-case 5% wall/CPU retention gates in
FIXED-QUALIFICATION.md. Run each original three-cycle, five-edit protocol using
bench_e2e_workflow.py and its independent repeated-workflow verifier. Require
identical bytecode on both sides of every source state. Keep the matched
component tools from installed-tools.json; their only difference is the VM.

Cases may run in a different order when storage admission permits a smaller
case first. An admission refusal is recorded before any benchmark command or
source edit. Do not repeat an executed failing timing gate. Every case remains
required; a smaller case cannot stand in for a large case.

Keep the existing complete-cache estimates for Nushell type relations, Ruff
and Nushell parser. For basic pgrust, use the four completed
whole-call-space-pgrust-{native,baseline,candidate,check}-archive-01 inventories:
native objects were retained in that inventory. Include 20% growth, the 8 GiB
running floor, the original check archive reserve and 256 MiB for evidence.
The remaining cases retain the conservative 4 GiB cache estimate plus 20%,
8 GiB running floor, 2 GiB archive reserve and 256 MiB evidence. These estimates
are admissions, not reservations against other users of the shared volume.

Freeze the recipe, original corpus configuration, verifier, tool receipts and
qualification reports before each history. Retain all failures and raw local
evidence. Private-case results publish only aggregate times, counts and hashes.
