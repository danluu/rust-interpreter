# Related pointer ranges within one native region

The checked-address timing screen and whole-function local-fact census are
complete. Both leave their immediate runtime proposals parked. Current typed
counts locate many unknown addresses in generic SipHash rounds, determinization,
sorting and scan helpers. Count related addresses before implementing a broader
guarded native path. No project-name specialization or external guest backend.

Analyze each exact saved native interval independently. Track bounded symbolic
pointer expressions originating from a register's value at region entry or an
eight-byte, in-frame slot's value at region entry. Explicit register writes kill
the old identity; typed copies, full-width loads/stores and bounded constant
pointer offsets can propagate an identity. Preserve source-before-destination
semantics for aliases. Unknown memory writes invalidate slot-value knowledge;
known overlapping writes invalidate their exact ranges. A dirty slot cannot
later be mislabeled as its entry value. Already loaded register values retain
their old identity when the slot changes. New opaque loads are not entry roots.

Count positive fixed-size Load/Store and Copy endpoints by common entry root.
Record offsets, read/write requirements, enclosing extent and checks per group.
Consider at least three accesses within a bounded 4 KiB extent; report the best
single group per interval and all-group totals separately. Weight by exact saved
native interval entries. These are conditional opportunities, not proven emitted
savings, hardware traffic, guard hit rates or elapsed-time predictions. Keep
unmodeled accesses and analysis declines visible. Do not infer pointer equality
from names, current values or matching formatted opcode text.

A later emitter would preflight the entire range once, then use a fast body.
If that stronger check fails, the original ordered operations must execute with
their original partial writes, errors and instruction accounting. The preflight
must itself read only valid entry registers/frame bytes, run under the existing
entry/readiness contract, and consume no guest operations. It must prove offset
arithmetic and arena classification, including tag crossings and wraparound.
No signal faults or blanket unchecked memory. Declining to the custom interpreter
may avoid duplicating a slow native body, but progress/fallback and budget behavior
need explicit proofs and real fault tests before implementation. This census
authorizes none of those execution changes by itself.

Qualify provenance/alias/offset/boundary tests and the existing offline CLI modes,
then run three censuses on the adopted, hash-bound profiles. No guest execution
or timing pair is added. Serialize under the shared lock, 45-second admission,
two Cargo workers and an 8 GiB floor. Preserve other sessions and all evidence.
Implement a candidate only if eligible groups cover meaningful current work;
otherwise retain the negative result and choose another direction.

Reports retain at most ten groups per function and 64 sites per group, with
explicit truncation flags and full aggregate counts. The first build requires
466 workspace Rust tests per profile (nine new provenance/group tests), one
ignored test, and a separate snapshot of the offline executable. No VM tool
installation or execution-path change is part of this diagnostic build.
