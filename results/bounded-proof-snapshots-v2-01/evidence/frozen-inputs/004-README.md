# Referenced proof snapshots

This separate helper preserves the original v1 helper and every existing frozen
caller. It is a source proposal until its bounded controls and caller integration
are reviewed and executed. It does not authorize a compiler, provider probe or
application workload.

`measure(records, limits, guard, *, reuse=None, evidence_roots=None)` and
`write_verified(records, destination, projection, limits, guard, *, reuse=None,
evidence_roots=None)` keep the old positional arguments. With no references they
still write each unique selected payload once. The original seven fixture tests
are copied byte for byte and target this module through their ordinary import.

Each reference has exactly `path`, `identity`, `blob`, and `evidence_root`.
`identity` has the same seven fields as an ordinary frozen input. `blob` has the
original five fields: `filename`, `logical_sha256`, `logical_bytes`, `sha256`,
and `compressed_bytes`. `evidence_roots` maps exact canonical predecessor root
paths to full frozen directory identities. Every declared root must be used;
roots cannot overlap. Every referenced file must be ordinary, single-link,
strictly beneath its declared root, and have the exact logical-hash filename.
Duplicate logical hashes, paths or inodes in the reference selection are refused.

The caller must bind each selected reference to the predecessor's closed receipt,
projection, manifest, actual audit, and frozen bytes. The caller also proves that
every allowed predecessor root already appears in its aggregate evidence scan.
The helper does not infer those facts from a pathname, receipt label, or file
content. No global blob search is performed. The projection binds the complete
explicit reference selection and root identities; a subsequent write recomputes
and requires exact equality with that projection before creating its destination.

All original source records and every duplicate logical alias are still read and
verified. Both new and reused gzip payloads receive compressed hash/size checks,
full decompression through gzip EOF and logical hash/size checks. Reference routes
and frozen identities are checked before and after reading. No old file is
modified, copied, moved, hard-linked or unlinked. New output cannot be inside a
referenced root or contain one. The new directory contains exactly the new blobs;
an entirely reused selection produces an empty new blob directory.

The v2 projection retains `files`, `blobs`, `logical_bytes`,
`unique_logical_bytes`, `compressed_bytes`, `compressed_allocated_bytes`, and
`manifest_reservation_bytes`. These describe the complete selected proof,
including reused payloads. It adds:

- `storage`: each logical hash has `kind: stored`, or `kind: reused` plus its
  exact predecessor path.
- `reuse`: each reused logical hash maps to its complete supplied reference row.
- `evidence_roots`: the complete supplied root identity mapping.
- `new_compressed_bytes`, `reused_compressed_bytes`, and
  `new_compressed_allocated_bytes`.

The manifest contains those reference and accounting fields, with an actual path
for both kinds in `storage`. Its `files` mapping retains every original logical
path and points to the appropriate physical gzip. Total logical and compressed
limits still apply to the entire proof, including references. The stage's
physical reservation is its measured current aggregate allocation plus only new
blob writes, the existing per-record rounding allowance, and the unchanged
document and remaining-output reserves. Reused bytes are never subtracted from
the current aggregate and never credited twice. The stage must separately verify
that all referenced roots are included in that current aggregate observation.

Independent auditors must check the full selected logical set, the exact stored
and reused partition, every referenced predecessor association, all file/root
identities, all blob bytes and gzip EOF, and exact new-directory membership. A
standalone archive must include every referenced blob plus the full original
logical/physical mapping; a path-only manifest is not a standalone publication.

The generic helper makes no completion or durability claim about its caller. A
stage must bind the predecessor's closed writer and fsync/readback evidence,
retain all failures, and continue checking current aggregate allocation and free
space through its existing guard. None of the evidence, admission, output,
logical-file or compressed-payload limits is lowered by this proposal.
