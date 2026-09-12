# Reuse stable block liveness transfers

Status: unqualified source candidate. No builds, tests, benchmarks, or performance
claims accompany this commit. Base: `b767335`.

The scalar-frame planner repeatedly applies the same immutable block events to
the union of successor input sets. Aggregate relocation calls this same planner.
When that union equals the block's previous output row, the corresponding input
row and event-work charge are unchanged. Reuse those existing rows and retain one
optional work charge per block; do not allocate another liveness matrix.

The cache is local to one `plan_with_eligibility` invocation, after eligibility
filtering. `None` means the block has never been evaluated; `Some(0)` is a valid
completed transfer for an empty block. An unchanged successor union can reuse the
previous input directly because no other block writes that input row. Every miss
runs the original event loop, including its read/write order and per-event bound.

Hits still add the exact original logical work charge and apply `MAX_WORK`.
Each event's charge is positive, so testing the total cached charge gives the same
accept/decline result as the original event-by-event checks. A prior successful
charge and the current accumulated work are each at most `MAX_WORK`; their sum
fits `usize`. Empty blocks have zero charge and cannot cross the limit.

Keep reverse block sweeps and their convergence rule unchanged. A hit cannot
change its input, so it leaves the sweep's `changed` flag unchanged. All entry-zero
eligibility filtering, interference reconstruction and its independent input
comparison, greedy ordering, checked layout allocation, coloring certificate,
and publication of final eligibility remain unchanged. In particular, reuse
must not admit a function that the original logical work bound declined.

The expected beneficiaries are bodies requiring multiple liveness sweeps,
including blocks that stabilize before their neighbors and the final convergence
sweep. One-sweep bodies gain no cache hits and incur comparison overhead. Existing
stage timings do not isolate this loop, so a useful build-time improvement remains
unproven. This change is independent of byte-write coverage ownership and owned
leaf inlining.

## Prepared correctness checks

`scalar_frame_liveness_tests.rs` retains the complete original planner from
`b767335:crates/mir-export/src/lower/scalar_frame.rs`, changing only its name.
The original function text, without the following blank line, has SHA-256
`861901d1b1d000f1456dbece95428832d7e16a779f6e8cec0213a37f5843d387`.
It uses the unchanged `Dense` operations, performs every original event scan, and
does not invoke the candidate planner or any cache helper.

Five tests compare full slot offsets/sizes, extent, success/decline, and the
caller's eligibility output against that reference. They cover first evaluations
with empty output, zero-work transfers, delayed propagation through empty blocks,
loops, joins, unreachable blocks, dead stores, same-event reads and writes,
alignment and zero-sized locals, plus 512 deterministic CFGs including bitset
word boundaries. Input bounds and checked extent overflow remain represented.

Four explicit work-limit fixtures have logical charges `MAX_WORK - 1`,
`MAX_WORK`, `MAX_WORK + 1`, and `MAX_WORK + 2`. They require the unchanged-output
second sweep. The last two distinguish a late interference decline from a decline
within the repeated liveness transfer; neither may publish changed eligibility.
The charge formula comes from the fixtures' event counts and live-set sizes, not
from the candidate implementation.

## Qualification still required

Run the focused exporter tests and the repository's required debug/release and
native/differential/rejection checks under the shared workload lock. Confirm
byte-identical public artifacts, unchanged diagnostics and planner decisions,
using the same frozen VM and launcher for baseline and candidate. Before timing,
freeze a separate build-time comparison plan and its gates. Retain failed runs;
this source design establishes no performance result or adoption decision.
