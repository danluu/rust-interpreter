# Census guarded external value forwarding with existing proofs

Adopted ordinary memory forwarding tracks local frame values. Existing guarded
ranges also prove complete external offsets, and some prove disjointness from
the complete active frame. Observe only those frame-disjoint plans, current
region-local original register facts, and1/2/4/8-byte Load/Copy reads.

Track at most16 values from guarded Loads/Stores or value-known Copies. Register
redefinitions invalidate owners; reuse requires the owner still in the current
fact table. Overlapping external writes invalidate ranges, unknown writes clear
all entries, and proven local writes preserve them under the existing disjoint
guard. A new region starts empty. No constants or facts are introduced. Query
Plan::displacement immutably; do not call the emission helper that adds live-ins.

Three Rust controls/profile cover overlap/unknown writes, register availability,
redefinition, eviction, boundaries, active disjoint plans and no synthetic live-ins.
Two Python ownership controls and three exact code reconstructions bind the same
adopted block/exhaustive/parser captures. Join exact original PC spans to closed
normal-entropy samples. Seven commands, no guests, executable publication, new
checks or runtime change. This is narrower than full scalar path/store-log work.

Sample scope is partial and perturbed; no removed-latency claim. Only material
scope warrants an actual forwarding candidate with independent memory/fault
controls and unchanged real-edit gates. Shared lock, shared ROOT target, two
workers, max(14 GiB,8 GiB+twice target allocation) admission and8 GiB child floor.
