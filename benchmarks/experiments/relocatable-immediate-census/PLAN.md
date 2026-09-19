# Conservative immediate-relocation coverage before a runtime design

The actual miss join assigns152ms of overlapping emission to2563misses whose
intervening Function changes are only immediate values. Measure a narrow subset:
a definition used only as Store source before overwrite, with no later memory
read/helper in its native region and no live value escaping the region (unless
superseded by a later definition). Use existing full-CFG liveness; decline on
analysis bounds. Preserve the exact native-region boundaries/1024-op split.

Only the literal bits are normalized in this offline fingerprint. Retain each
half's upper16-bit nonzero pattern, matching MOVZ/MOVK length. Include the selected
PC list and all other Function fields, operands, names and IDs unchanged. Require
old/current normalized signatures to match before counting a possible relocation.
This is a coverage bound, not a sufficient native-template identity: callee/scalar
admission, other emitter passes, placement and complete relocation ledger still
need proofs. No production code, key or cache policy changes.

Five controls/profile cover exact width shapes, disallowed arithmetic/address/
branch uses, memory forwarding, live successors, overwritten definitions, liveness
bounds and region-size split. Then one explicit ignored release census decodes and
fully validates the eight original artifacts, using actual per-worker miss
attempts/hash-bound intervals. No JIT construction, guest or executable publication.
Retain all input/output identities and aggregate only the five valid edits.

Two Cargo/testworkers; shared benchmark.lock45s; dedicatedtarget neverclean;
buildfloor max(14GiB,8GiB+2*allocated target),child/closure8GiB. No goals/subagents/
peerwork changes. Existing runtime evidence remains independently closed.
