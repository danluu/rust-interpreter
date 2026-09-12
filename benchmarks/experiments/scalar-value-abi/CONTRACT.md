# Scalar value ABI contract, first implementation

Base: integrated `5b2330c` / `9637b0ac`, excluding the parked runtime/compiler
candidates. Admission `scalar-boundary-admission-01` passes eleven tests using
the unchanged scalar transform, admits 453 folded/1,542 token boundary slots,
and reconciles both original profiles. Token admission covers 85.80M direct
argument copies and 47.66M result returns. No probe body has executed.

## Artifact and semantic model

Keep the existing `Program`/`Function` structures and all version-5 bytes intact.
A companion `Artifact` contains a Program plus a dense function ABI table.
Version 5 serializes only the original Program; version 6 serializes Program
followed by the ABI table. Inspect the first little-endian version word before
choosing the bounded decoder and reject trailing bytes. The inner Program carries
the same version, so passing a scalar body to the old execution API is rejected.
No reserved pointer/register bits or frame offsets encode ABI meaning.

Each version-6 function has one `Option<Reg>` per ordinary argument and one
optional result register. `None` retains the corresponding frame slot; `Some`
receives/returns a scalar value whose width is the existing slot size. Only
1/2/4/8/16-byte scalars are allowed. Check table/arity, register bounds, unique
argument registers, widths and resource bounds before any execution. A result
may name an initialized argument register, permitting identity functions.
Scalar artifacts require full checking; version-5 partial-mode compatibility
remains unchanged. Compiler eligibility is a separate strict MIR/address proof.

## Implementation sequence

1. Implement and qualify bounded versioned serialization and ABI validation.
   Keep these in an isolated source build. No scalar guest executes at this step.
2. Implement custom-interpreter calls, indirect calls, root arguments/results and
   TLS entry/return using the table. Existing address-based Calls bridge to scalar
   callee registers in argument order; scalar results bridge to the caller's
   memory destination. Preserve existing allocation, memory-fault and depth-error
   order, including partial argument failures. Initialize register backing before
   publishing inputs; preserve width and upper-bit behavior. No stale values.
3. Extend native resumable Calls/Returns with the same contract and exact
   continuation/budget/profile behavior. The native entry already crosses guest
   frames without host recursion. Historical whole-tree modes must either
   understand the ABI or explicitly decline before progress. Keep the ordinary
   version-5 path and its bytes/behavior qualified.
4. Extend explicit call operands/results to carry values directly from/to caller
   registers, with typed enums and version-6 opcode validation. This is necessary
   to remove caller materialization as well as callee storage. Keep address
   operands for mixed/escaping/aggregate cases and indirect-call bridges.
   Preserve failure order when replacing address reads with value operands;
   only proved valid caller-frame reads may move before a Call.
5. Integrate the compiler's typed selection and complete address-use proof after
   current relocation/inlining/CFG work. Initialize promoted arguments from the
   ABI, not an Imm(0). Promoted results retain required zero initialization and
   publish only on Return. Address-exposed storage remains real memory. Admit
   caller Call operands only with an explicit value-consumer proof; the old
   promoter's blanket Call exclusion cannot simply be deleted.

The address-bridge implementation is a correctness milestone, not a substitute
for caller value operands. Before timing, freeze the completed compiler/runtime
candidate and its admission bounds. A separate bridge-only measurement may
attribute gains, but cannot redefine the full value-passing objective.

## Qualification and decision

The existing scalar transform's address proof is insufficient to establish entry
initialization, return publication or ABI compatibility. Add direct/indirect,
mixed/recursive, root and TLS tests; all scalar widths; upper bits; stale backing;
short budgets; cold assertions; partial copy failures; malformed metadata/opcodes;
tracked-caller and strict uncalled type/borrow rejections. Run interpreter/native
differentials and original real test assertions. No fake threads/unwinding,
external guest interpreter/JIT or LLVM guest fallback.

Use fresh three-cycle, five-edit interleaved A/A and candidate histories with
checking floors, child CPU, restored source and all pairs preserved. Token must
improve complete-command wall time by at least 10% beyond A/A variation; folded
has separate 5% wall/CPU guards. Then run all seven held-outs, including the
private aggregate-only workflow. No threshold tuning of the parked experiments.
The compilation/runtime split and absolute native times remain visible.
