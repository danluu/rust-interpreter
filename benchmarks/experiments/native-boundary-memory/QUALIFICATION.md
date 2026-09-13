# Qualification before the combined screen

Baseline complete tool35df4077 uses adopted VMf0e5f2ea. Keep its exact exporter,
wrapper and standard-MIR sysroot. The new bundle changes only native memory
operations, adds two controls and restores two qualified paired-register controls.
The expected workspace total is519 passed/profile (406 bytecode +113 exporter),
with six explicitly ignored controls. Preserve both ordinary and resumable modes.

Use the existing owned build target,16 GiB initial/8 GiB child floors, two Cargo
workers, nonincremental host build, debug information disabled for debug/test and
release debug=1, matching the earlier adopted runtime build. Freeze the exact
source revision, compiler component hashes, input files, commands and outputs.
Publish a new immutable composition key only after both suites and release VM
build pass. No exporter rebuild or LLVM guest path is part of this candidate.

The local assembler has independently verified SIMD zero stores and the existing
directional pair-copy encodings. Fixed clears use SIMD at64 bytes and above;
bulk clears use256-byte batches when the guaranteed extent is at least256,
otherwise64-byte batches when admitted. Exact scalar tails remain. Copying uses
the existing16-byte directional helper only above the old128-byte ABI threshold.
The broad dirty-memory and overlap oracles cover both thresholds, sizes136/304,
all64 alignments, prefix/suffix canaries and preserved x16/x17/x22 call state.

After build qualification, run original strict/cache/Cargo controls and real
test selections with the same pinned sources, valid/wrong edits and restored
originals. Bind an exact candidate profile to each saved original corpus before
interpreting instruction/code changes. No timing evidence is borrowed from the
prior paired-register experiment. One combined primary screen decides whether
the full five-case comparison starts; a failed screen leaves it unstarted.
