# Runtime scalar graph feasibility

Preserve the V5 compiler output, strict checking, function/frame identity and
original PCs. This prototype replaces only a proved, small, acyclic leaf's
private frame bytes with symbolic scalar values. It is an offline diagnostic
with its own reference evaluator; production interpreter/JIT behavior is unchanged.

Initialize symbolic bytes and virtual registers with the original zero values,
then write scalar arguments in ABI order, including overlapping slots. Known
Copy/CopyDynamic operations snapshot source bytes before replacing destination
bytes; FillBytes uses the low byte. Reassemble little-endian loads from those
byte identities, forwarding exact values when their upper bits are known zero.
Merge registers and bytes with explicit predecessor-dependent phi values.
Local-derived address bits retain the original logical base and offset. This
does not claim nonescape; it keeps addresses observable in the reference model.

Dead-value elimination roots returns, switches, assertions and every division
or remainder that can fault, even when all result registers are dead. Maintain
the original-PC sequence and budget charge for every instruction, including
eliminated memory operations. Reject reachable cycles, missing terminators,
unreviewed operations, unavailable memory proofs and resource exhaustion.
Maximum shape is 512 operations/registers/frame bytes, 8,192 CFG edges,
16,384 nodes, 250,000 scalar work units per function, and 128M globally.
Failed lowerings conservatively consume their complete local work allowance.

Five controls compare the value graph with this project's ordinary bytecode
interpreter: 2,187 overlapping-copy cases; branch/phi and every-budget accounting;
ordered overlapping arguments; returned Local address bits; dead division faults;
assertions/traps; integer widths and output aliases; dynamic fills/copies; bounded
rejection. Integer arithmetic reuses the VM's explicit semantic helper, so these
are independent memory/control-flow checks, not an independent arithmetic oracle.
Run both debug/release alongside all 13 prior access-proof controls.

No original project guest executes during the census. Analyze the pinned original
token artifact, report nodes after elimination at exact original PCs, and join
that report to existing counts. These are IR operation counts, not native time.
Setup and whole-artifact analysis cost are retained, not assumed to equal future
lazy runtime preparation. Keep two Cargo workers and the existing lock/disk rules.

Before native execution, an additional call-boundary contract is mandatory.
A speculative attempt may use private storage only after proving original
resource/capacity/depth/budget admission and valid preexisting argument/result
ranges. Failure must leave caller state and all guest-visible counters untouched,
then execute the original Call with its original error ordering. Success must
commit exact results, retained alignment padding, peak/live memory, instruction
and per-PC counts, native transitions and caller register state. Local address
escape, result/frame aliases, partial errors, original register backing, code
admission fallback and profiling remain unqualified. This reference evaluator
does not implement or certify that call protocol. Direct AArch64 code generation
and complete changed-source comparisons follow only after that qualification.
