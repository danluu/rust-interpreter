# Closed failed-owner snapshot catalog (source draft)

This separate successor adds `extend_failed` to the previously qualified
successful-owner catalog. It reads saved metadata through authenticated callbacks;
it performs no filesystem access, import of an application module, compression,
provider probe, command, or write. These sources and proposed tests have not run.
The original catalog01 and its actual 33-control proof remain unchanged.

`extend_failed(prior, owner, accounted_roots, limits, *, read_json, file_record,
directory_record, expand_inputs, validate_failure)` accepts an owner with exactly
`role`, `source`, `evidence`, and `audit: {path, sha256}`. Its terminal must remain
`failed`, with its original nonempty error and finite, ordered admission/finish
times. The independent audit must have `status: verified-retained-failure` and
exact `receipt_sha256`, `inputs_sha256`, `plan_sha256`, `snapshot_plan_sha256`, and
`source_snapshots_sha256` associations. It never reads or fabricates a result.

`validate_failure(owner, terminal, audit)` receives independent JSON copies and
must return exactly `True`. The caller must authenticate the complete actual
failed raw history, original error, explicit outer and launcher closure, absent
unexecuted roles, and any owner-specific required absent result/artifacts. For
the original failed hash driver this is the one failed compile, zero serial or
parallel driver processes, zero qualified hash processes, and an absent result.
Those driver-specific facts belong in its separately reviewed failure auditor
and callback; a generic boolean manifest cannot establish process closure.

Successful `extend` keeps its old result/receipt/audit contract. Both routes use
the same `_snapshot_catalog` body, extracted from the original successful route:
all logical members and aliases, raw compact SHA and complete expansion, helper
source association, retained projection, stored/reused physical maps, exact
root membership, single-link identities, duplicate inode rejection, and total
versus new allocation remain checked. Callback arguments cannot modify the
retained owner. The failed route additionally rechecks every initially loaded
metadata file record and decoded view after all callbacks. `read_json` may return
a separately authenticated expanded plan while `file_record` retains its actual
raw compact-file identity and SHA; the enclosing reader owns that conversion.

A catalog containing a failed owner has explicit policy
`closed-failed-proof-snapshot-catalog-v2`. Its predecessor association includes
`completion: failed` and the exact receipt/audit/source/snapshot references, with
no result reference or result digest field. `select` and `validate_catalog`
retain that distinction. A later successful owner can extend this catalog; its
own success association does not relabel the prior failure. Removing the failed
policy, adding a success result to that association, or changing its document
routes is rejected. All-success catalog output retains the original policy.

The caller must rebuild the entire predecessor qualification before extension
and perform qualified v2 `verify_reference` readback on **every** returned physical
row, including rows not selected by the new owner. This supplies the actual
compressed hash, logical hash/length, CRC and gzip EOF proof. The pure catalog
checks authenticated descriptors and does not claim to decompress gzip itself.
Every blob remains beneath an explicitly counted evidence root. No old allocation
is subtracted, no blob is moved or hardlinked, and no limit changes: 1024 logical
records, 64 MiB per file, 512 MiB logical, 128 MiB total compressed, 4 MiB per
manifest, and the enclosing unchanged 256 MiB evidence cap. Standalone retention
must include all referenced blobs and source/alias mappings.

`test_catalog.py` is a byte-identical copy of the original 33 tests.
`test_failed_catalog.py` adds only tiny in-memory fixtures: complete failure
retention without a result read, compact input association, successful extension
after failure, audit/status/closure corruption, typed times, every metadata
digest, callback mutation, missing source/alias/EOF, accounting and inode
collisions, and explicit failed-lineage policy preservation. Synthetic compressed
descriptors are labeled as such; these controls make no live-provider or actual
gzip qualification claim.
