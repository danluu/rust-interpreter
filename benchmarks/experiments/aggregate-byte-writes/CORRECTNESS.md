# What the experimental layout proof covers

The candidate changes a checked Rust function's local storage layout. It does
not change type/borrow checking, the guest instruction implementation, frame
initialization, argument/result byte counts, or the direct AArch64 emitter.
The isolated build recipe binds every copied source and the immutable parent
VM/wrapper. This document explains the invariants; it is not a formal proof.

The retained backward dataflow computes whole-local liveness. A write kills
incoming liveness only when the actual emitted span covers every byte of the
local and contains no known overlapping read. Partial/uncertain writes also
read the incoming local. Therefore field writes, inactive enum bytes, padding
holes and hidden read/modify/write lowering cannot silently inherit another
local's previous bytes. Every initially-live local remains dedicated. Writes
whose values are never read still interfere with all live locals they could
clobber. The coloring is checked independently against these interference sets.

Call destination writes belong to a synthetic normal-return edge. Exceptional
successors bypass it, including when a cleanup and normal edge reach the same
original block. Actual completed callee slot sizes establish a direct Call's
result write and argument reads. Intrinsic lowering is analyzed as emitted
operations, not assumed to perform a whole result copy. The caller's argument
values have been copied into the callee before a normal result copy can reuse
their storage. An address passed as part of a value has already made its
underlying MIR local ineligible through the address-use visitor.

Locals with references/raw addresses taken, drop contexts or unknown contexts
remain dedicated. A dereference reads the pointer-bearing local's value; it
does not write the pointer's own slot. Index operands are explicit reads.
No eligibility rule depends on a project name, type display string or profile.
The frame remains one VM allocation; this pass does not add pointer provenance
semantics or make invalid Rust pointer arithmetic defined.

Previously colored scalar locals can share an old physical offset but receive
different new offsets. Each named Local operation therefore records its MIR
local at construction, using its fresh destination register. Existing scalar
promotion removes some of these operations and preserves surviving destination
IDs. Calls and control-flow optimization run after relocation. Every surviving
named address must match its recorded old slot. Missing origins below the old
local extent decline the complete function. Anonymous scratch/caller-location
addresses occur after that extent and shift by the same multiple of frame
alignment. The new local extent cannot overlap the shifted scratch region.

ABI locals remain dedicated. Return layout is checked against local zero;
positive-size arguments must have exactly one containing dedicated formal local
(tuple-spread fields retain their relative offsets), or be trailing caller
storage. Zero-sized return/local addresses retain valid aligned slots; the
existing lowering elides zero-size arguments. All additions/subtractions are
checked. An independent physical-range check allows only identical eligible
shapes to overlap. All replacement addresses/ABIs are prepared before mutation;
failure leaves the complete original function intact.

Qualification includes the original scalar planner tests, 10,000 independent
byte-coverage cases, 16,807 full/partial/dead-write sequences, cleanup-edge cases,
relocation/ABI/overflow rejection tests and native differential execution.
The focused run checks 1,024 VM executions across four fixtures, two compiler
policies, both exporter versions and both engines. Original folded/token
assertions pass with fresh changed artifacts. This is targeted coverage, not
proof of all Rust behavior. Broad existing native/TLS/fre checks and held-out
workflows remain required if the performance gates pass.
