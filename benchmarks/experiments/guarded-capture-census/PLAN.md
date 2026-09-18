# Count private value captures within existing external guards

The prior guarded-value observer required an original register fact to remain
available. This disabled model instead retains complete 1/2/4/8-byte values in
four hypothetical private native slots, only inside an existing frame-disjoint
whole-range guard. It adds no new guards or generated instructions.

Each exact guarded Load/Copy source may reuse an earlier capture. Source misses
and guarded Store/Copy destinations create captures; all original writes remain
immediate. Partial overlap invalidates affected cells; unknown writes clear all
cells, and proven local writes preserve them under the existing disjoint proof.
Register redefinitions are irrelevant to private captures. Each region starts
empty, with deterministic FIFO replacement and a fixed four-slot limit. Record
all capture overhead, including unused captures, and associate each reuse with
its original producer. No offset matching across different guarded roots.

Three Rust controls/profile cover an independent byte-write oracle, capacity and
width identity, register eviction, unknown writes, boundaries and observer cleanup.
Three Python controls qualify original operation and fine payload/address ownership.
Reconstruct every retained block/exhaustive/parser native word and entry. Emit only
diagnostic spans, and count samples in original source guarded-address/load words,
excluding destination addressing and register publication. Seven commands, no
original guest or native publication. No removed-latency prediction or dynamic
capture count follows. Only material scope justifies a concrete cost-filtered
native cache and independent memory/fault/budget/ABI tests, then the existing
changed-source primary and conditional full guards.

Use the shared lock, shared ROOT target, two workers, conservative build admission
max(14GiB,8GiB+twice allocated target), and8GiB child floor. Keep adopted runtime,
strict checking, peer work, old failures and all performance gates unchanged.
