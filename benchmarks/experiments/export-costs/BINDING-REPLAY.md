# Reconstruct a second exporter graph from owned binding recipes

The dependency observer supports a reuse experiment. Before loading an older
payload, prove that owned instructions and frame observations can recreate the
same graph using current MIR.

Record each graph interaction in lowering order: constant operands identified
by their ordinal in the current MIR visitor, direct calls and drops by block,
function-pointer casts and TLS references by statement, caller locations by
terminator, errno allocation, indirect-call shapes and unavailable-call
diagnostics. Record immediate destinations and typed direct-call identities.
Do not serialize compiler AllocIds, DefIds, types or borrowed compiler data.
Decline an unsupported recipe, including direct dynamic-vtable construction;
the second graph lowers that complete function normally.

Serialize and decode an owned function, its complete frame-packing observation
and its event tape. Replay supported tapes in a second exporter seeded with the
same entries. Resolve all compiler constants and instances from the current MIR
and replay recursive allocation materialization normally. Patch only recorded
immediate registers and typed direct-call fields, including calls retained in
frame observations. Keep graph scheduling, allocation addresses, TLS, statics,
alias classes and diagnostics identical. The compiler's caller-location hook
creates fresh IDs when called again: compare addresses for shared IDs and the
cardinality of every guest-address alias class, not numeric compiler-ID equality.
This never merges allocations by equal contents. Compare every reconstructed function and
frame observation against full lowering, then compare exporter graph state.

The opt-in flag requires ordinary strict checking and function-cost observation.
All original functions are still fully lowered. This first reconstruction is
within one compiler session; it does not establish cross-session reuse, actual
skipped work, or an end-to-end saving. Key construction, persistent storage and
cache publication remain further work.

Qualify the existing seven complex fixtures against native assertions and both
engines at three seeds. Retain the original retained/off/on exports, including
the actual TypeId trace control, and add a separate replay export. Expect 231
commands: seven fixtures times 32 commands, plus seven strict/error controls.
Require identical executable artifacts and complete graph-replay reports. Then
run the existing small semantic-edit fixture and token/folded histories if the
basic reconstruction succeeds. Keep failed checks visible and repair the
identified cause; these are correctness diagnostics, not timing retries.
