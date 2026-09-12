# Bounded constant folding, then call specialization

The first census found useful constant sizes, alignments and flags, but also
constant caller-location pointers. Do not select compiler rules by function name,
project or measured profile. Keep this implementation off main until qualified.

First implement a generic function-body constant folder. This is the prerequisite
for useful specialization and will be measured separately. Track scalar values,
symbolic in-frame Local addresses and exact local bytes in a bounded forward
must-analysis over basic blocks. Entry values are unknown. Propagate all CFG
edges, including both sides of known switches, and intersect facts at joins.
States can only lose facts after first arrival. Recheck every edge against the
final states before using any fact. Decline on work/shape/storage limits.

Unknown writes/calls invalidate local memory; precise local writes invalidate
all overlapping bytes. Recognize bounded local fills/copies and exact integer
semantics, including aliased value/overflow writes. A local address plus a known
nonnegative offset is a Local fact only when the entire resulting address remains
within the validated frame; the frame's allocated end bounds the machine-width
addition. Never treat unknown pointees or initial zeroes as constants.

Replace proven scalar results/valid local or immutable-data loads by constants;
fold proven switches. Keep potential faults and memory effects. Remove only dead
pure register definitions using full CFG liveness, then reuse existing control-flow
cleanup. Preserve function IDs, layouts, all memory stores/copies, unknown loads,
unknown division/remainder and runtime checks. Instruction budgets count the
resulting artifact, as for existing compiler transformations. The VM is unchanged.

Per function: at most 4,096 operations, 8,192 registers, 256 blocks and 16,384
operand/edge visits; at most 512 register facts and 256 byte facts per state;
a two-million-unit solver budget and a separate existing bounded liveness pass.
Keep a global 32-million-unit solver budget per program and explicit decline
counts. Declines retain the original function, without partial rewrites.

Only after this pass is correct and its real-workflow effect measured, consider
bounded direct-call clones seeded from argument-byte facts. Preserve the original
callee and ABI, handle overlapping argument slots in copy order, limit clones and
code growth, and avoid specializing merely on unique caller-location constants.
Do not bundle unmeasured cloning with the initial folder. Use the fixed complete
edited-source token screen (10% wall improvement/no CPU regression), then guards
and broader real projects only after a pass. Failed stages stay parked.

Host qualification floor: 7 GiB. The first build stopped before Cargo at the
8 GiB admission check. After retiring exact terminal metadata with preserved
evidence, the host has about 7.5 GiB free. This nonperformance workspace build
reuses the existing target, uses two workers, disables incremental output and
fetches no dependencies. Admit each host child only above 7 GiB and record that
choice explicitly. This exception does not lower any guest-project export,
execution or actual-source-edit benchmark's 8 GiB floor. Do not retire more
historical caches merely to meet the former blanket host threshold.

Fault qualification compares exact original/folded interpreter errors. JIT
regions already report memory-range errors differently from interpreter fallback:
`JIT guest memory access failed` versus `invalid guest memory access`. Removing
dead definitions can cross the minimum native-region size, changing that wording
even in the same JIT mode. Treat exactly those two strings as one range-fault
category for JIT comparisons; keep every other error and instruction-budget
failure exact. Do not change the VM or broaden normalization to unrelated faults.

Exporter placement: after the existing call/inlining/CFG pipeline, run the folder
and then the existing CFG cleanup again. This makes the candidate exactly the
standalone typed transformation of the fully optimized retained artifact. The
extra cleanup cost is included in export time. The call-census CLI supports
`--fold` and `--verify-fold` with whole-artifact byte equality, preserving all
non-code fields. The verifier is untimed in subsequent workflow comparisons.
