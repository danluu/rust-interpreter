The next milestone removes caller memory materialization. Start from qualified
scalar native source; keep the fixed complete-command performance gates in the
parent scalar ABI contract. Do not time the address bridge as a replacement for
this work.

Append a version-6-only direct `CallValue` opcode with explicit `Address(Reg)`
and `Value(Reg)` argument and destination enums. Preserve every existing opcode
discriminant and reject this opcode in version-5 artifacts, including partial
ones. Existing indirect Calls retain the qualified address bridge at this step.
No pointer bits or reserved offsets encode a value operand.

An argument value is truncated to the callee's declared scalar width. It may
initialize either a register formal or a memory formal. An address argument may
likewise feed either representation using the existing checked load/copy. Only
1/2/4/8/16-byte slots can have value operands; aggregates keep addresses. This
keeps storage selection separate from the ordinary Rust function signature.

The result destination may be a caller register even when the callee returns
through memory. The validator proves the destination register and result width.
The register is written only on successful Return, after the callee's execution;
it may alias an input register. Register visitation marks value destinations as
definitions and address destinations as reads. Argument registers are always
reads. Include the ABI's implicit result read at Return in all native analyses.

Guest frame descriptors need an explicit return-location tag. A boolean field
beside the existing TLS flag can preserve the 48-byte layout, with the existing
usize payload holding either an address or a register index. Name/document the
payload accordingly; check every layout offset and initialize every new field
on VM/native/TLS pushes, including reused descriptors. Never read struct padding.
Validate the tag and destination against the caller when accepting a native
continuation. Use no host recursion and no new per-call allocation.

Share the interpreter's ordered argument handling. Value inputs are read from
the caller's registers after any backing resize, using saved indices; native
code uses its proven stable backing. Preserve frame/memory/depth admission and
exact instruction accounting. Native Returns can store directly into validated
caller register backing before restoring the caller and reloading persistent
assignments. Keep root and TLS Return behavior unchanged.

Qualification must include all four argument storage combinations, both result
destinations, narrow/wide values, aliases, recursive and repeated mixed calls,
stale frame tags, unsupported indirect bridges, every budget boundary, code and
working-memory limits, per-PC profile agreement, and original version-5 tests.
The prior JIT/interpreter memory-message difference remains explicit. Prove hot
native Call/Return counters are nonzero, so fallback alone cannot pass the tests.

Compiler promotion follows runtime qualification. Remove the old blanket Call
exclusion only for operands covered by the typed value-consumer proof. Retain
all address-exposure/unique-definition/full-width/dominance checks and strict
rustc type/borrow checking. Preserve original assertions and freeze the final
compiler/runtime pair before fresh real-edit benchmark histories.
