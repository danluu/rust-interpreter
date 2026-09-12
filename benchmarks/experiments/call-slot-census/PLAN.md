# Native Call slot census

The integrated compiler is `5b2330c` / `9637b0ac`. The x22 budget ABI is parked
after missing its fixed complete-command gate. Next measure whether native
Calls repeatedly check statically known caller-frame argument addresses.

Use the existing successful control profiles from `budget-register-smoke-05`:
command 1 (folded trie) and command 11 (token phrase). Bind their original
artifacts, exact VM/options, stdout, stderr and profile hashes to the recorded
smoke receipt. No new guest execution, edit, runtime change or timing claim.
Keep token's actual entropy and reconcile each profile with its own total.

Build a small typed host diagnostic against the unchanged bytecode crate.
Validate Program and match every profile function, operation and vector length.
Compute native and interpreted per-PC frequencies from the recorded ranges.
Never infer semantics by parsing formatted opcode names.

Track Local and immediate facts inside semantic basic blocks, resetting at every
branch target and after branch/terminal operations. Calls preserve caller
registers. Kill all complete register writes using the shared exhaustive visitor;
model only unsigned 64-bit Local-plus-constant addition. Preserve aliased output
order. Unknown operations/addresses remain unknown. This is a conservative
opportunity count, not a proof for arbitrary external native-entry states.

Report weighted direct/indirect Calls, native/interpreted shares, nonempty
argument checks/bytes, in-frame/unknown slots, zero-byte operations, frame bytes
and potential local result destinations. Keep results distinct from observed
Return counts and CPU samples. Bound analysis per function; declined functions
remain in denominators. Cover branches, skipped definitions, aliases, overwrites,
frame bounds, zero-size slots and malformed profiles with deterministic tests.

Before any runtime optimization, audit external and descendant VM re-entry.
Static facts alone cannot authorize deleting checks if the entry contract
permits arbitrary initialized registers. A guarded specialization must fail
back before effects and retain original faults, charging, copies, clearing and
profiling. Host pointers cannot survive memory reallocation. The census will
choose the next implementation; it does not predeclare a speedup.
