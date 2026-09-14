# Saved scalar-body word census

The guarded scalar Call revision failed its unchanged 40-command primary gate.
Before another runtime revision, inspect its exact qualified saved AArch64 bodies.
This first census requires no host compilation, native code publication or guest
execution. Constant propagation in the scalar IR remains a separate next question.

Recognize only instruction encodings emitted by the current scalar emitter.
Reject unknown encodings, external edges and cyclic machine CFGs. Track integer
registers, SP, NZCV and the emitter's vector scratch register. Compute register
liveness and iteratively discard only pure register definitions whose results
are dead. Preserve every memory access, stack adjustment, branch and return.
This deliberately leaves dead spills and memory-mediated simplifications alone.

An unconditional Trap is emitted as `CMP XZR,XZR; B.EQ failure`. Its impossible
fallthrough can make the syntactic machine graph cyclic even though the original
scalar graph is acyclic. Prune that exact edge only when the CMP is the branch's
unique predecessor. Preserve the first census's fail-closed observation of this
case; it did not indicate an execution bug or establish savings.

Report static candidates and minimum/maximum candidate words along successful
paths, multiplied by the already recorded successful scalar Call count. Branch
feasibility is not inferred; bounds may be loose. Failed private attempts are
excluded. These are source-guided word-execution bounds, not sampled hardware
instructions, cycles or a speedup estimate. No one-to-one mapping to original
bytecode PCs is fabricated.

Bind source, terminal profile qualification, maps, raw code and original-PC
counts. Reuse the qualified independent full-byte reconstruction recorded by
the operation maps and validate its ownership protocol again. An unrecognized
body is a failed census, not zero savings. Tests cover flag use, MOVK read/modify/
write behavior, SP versus XZR, divergent paths, memory effects, failure returns,
unknown encodings and loops. All analysis is serialized by the benchmark lock;
the 8 GiB child floor and a 10 GiB analysis admission apply. Existing Cargo build
admission is unchanged.
