# Adjacent small-memory accesses: eligibility only

Use the closed adopted-code memory-operation-parts captures and their typed
Load/Store/Copy metadata. Inspect only load_data/store_data spans of16-byte
accesses. Match adjacent unsigned-offset64-bit LDRs or STRs with the same base,
consecutive offsets, no writeback, and an offset representable by one LDP/STP.
Reject load destination overlap with the address base or duplicate destinations.
Do not change validation, addressing, publication, native ABI copies or counters.

Validate decoding against independent assembler controls and negative unit tests.
Verify saved capture, partition, source-proof and exact-profile hashes before
counting; preserve complete function coverage and per-PC weights. Report both
instructions' sampled PCs as affected coverage, not time saved. The samples are
short perturbed ordinary-entropy windows; weights use separate bound-entropy
profiles. One fewer emitted word per eligible pair is not a latency prediction.
No guest execution, executable publication, re-sampling or runtime patch occurs.

Serialize all substantial parsing/auditing with benchmark.lock,45-second
admission,12 GiB initial free space and8 GiB child floor. Do not touch peer work,
reactivate the paused goal, retime parked candidates or start a new runtime
comparison without a useful coverage result.
