Runtime parent: caller-value tool e651b25cdf50df92a1787d99195803680d52cc25d0e98898f65ddbeb33393ed3,
qualified by results/scalar-value-calls-build-02 (319 debug/release tests, one
ignored). Source: .work/scalar-value-calls-build-02/tool-source. Native and
interpreter support explicit caller values; normal publication is still the
qualified version-5 compiler. No scalar performance comparison has run.

Implement typed MIR selection and real source-to-artifact publication next.
Keep strict rustc type/borrow checking and the fixed parent performance gates.

1. Reuse the boundary observer's typed layout/private-use evidence and its
   demonstrated argument-order/width binding at aggregate relocation. Add typed
   caller input/result candidates: full-place scalar Call operands and Call
   destinations can be value consumers/writers. Do not simply remove the old
   Uses/exclude_operand checks. Projected, aggregate, address-exposed, overlapping
   or ambiguous storage must decline. Include tracked-caller and spread arguments.
2. Carry candidate identity through the existing relocation, inlining, forwarding
   and CFG passes. Boundary argument/result slots can bind by ABI order/width.
   Ordinary caller locals need an explicit relocation map or validated unique
   Local-register anchors; their old offsets cannot be reused after packing.
   Inspect the existing relocation certificate before selecting the mechanism.
   Preserve optimizer passes and reject missing/ambiguous bindings conservatively.
3. Extend the actual final-bytecode address proof for Call operands. A candidate
   Call argument must be an exact full-width read of the private range, matched
   against the final callee signature. A Call destination is a successful-return
   definition of its full range. Require unique address definitions, dominance,
   compatible widths, and no unrecognized address consumers. Keep fixed bounds.
4. Allocate canonical scalar registers; formal arguments are initialized by the
   ABI, not Imm(0). Results retain specified initial zeroes. Rewrite caller
   operands to CallValue and attach the dense ABI table. Mixed and indirect
   address bridges remain valid. Do not use probe bodies as execution oracles.
5. Update Exported/serialization and the CLI wrapper/launcher capability contract
   together. main.rs currently validates/serializes Program, and interpreter.py
   explicitly requires bytecode_version==5. Publish Artifact version 6 only when
   the complete candidate is selected; retain exact version-5 controls. Keep
   output hashing, Cargo sidecar identity, partial-mode rejection and trace
   publication order correct. No LLVM or external guest execution fallback.
6. Qualify typed rejection/acceptance fixtures, strict uncalled type/borrow
   errors, real original assertions, unsupported cold code, recursive/mixed/TLS
   behavior, and native/interpreter differentials. Report admitted boundaries,
   actual value operands/results and exhausted bounds by typed operation data.
   Then freeze compiler/runtime and run fresh three-cycle, five-real-edit A/A
   and candidate histories. Token needs >=10% complete-command wall improvement
   beyond A/A; folded keeps separate 5% wall/CPU guards; seven held-outs follow.

The caller-value implementation's old local-address analyses now explicitly
invalidate value destinations; its compiler operand visitor is shared with the
bytecode visitor. It does not yet generate CallValue from MIR. Root integration
or a bridge-only timing is not a substitute for this compiler work.
