# Completed v2 proof catalog (source draft)

This pure adapter extends an independently rebuilt predecessor catalog with the
complete proof catalog of one successfully completed v2 owner. No preparation,
import, tests, compression, provider reads, or workload execution have qualified
this source yet. The existing beta/native v1 catalog and snapshot writer are
unchanged.

`extend(prior, owner, accounted_roots, limits, *, read_json, file_record,
directory_record, expand_inputs, validate_owner)` returns the same five catalog
fields (`policy`, `priority`, `predecessors`, `records`, `evidence_roots`) with a
new policy and one appended owner. `select(records, catalog)` returns only the
explicit physical references and roots needed by the caller's complete logical
selection. `reservation` computes new rounded bytes plus 4096 per newly stored
blob and the caller's unchanged document/output reserves.

The caller supplies an explicit owner role, source/evidence directories, actual
audit reference, `result_path`, and `result_digest_field`. There is no guessed
future result schema. The hash stage uses its existing `result.json` and
`result_sha256`; the existing source-preflight receipt instead names
`source-probe/result.json` through `source_preflight_sha256`. Any adoption still
requires the real independent audit with receipt/result hashes and a separate
owner-specific completed recipe validator. That validator must return exactly
`True`. The module binds the receipt's input hash to the actual input file and
that file's `plan_sha256` to the actual plan; it does not invent a hash receipt
`plan_sha256` field.

All callbacks are authenticated read-only operations. `file_record` returns
`{path,size,sha256,identity}` after checking the full route, current bytes and
seven-field identity against the enclosing freeze. Metadata and physical gzip
files must be ordinary single-link files. Logical source inputs may have their
original multiple links, which never grants additional physical reuse credit.
`directory_record` returns its stable current identity and exact sorted children.
`expand_inputs` calls the qualified generic file-table reader when needed; this
adapter also checks the raw base reference, retained base-file row, complete
disjoint union, typed table integrity, and unchanged non-file metadata. The
actual compact input SHA remains the receipt and projection identity.

Before `extend`, the caller must rebuild `prior` using its separately qualified
owner readers. Initially this is the existing beta/native v1 catalog, including
the failed native snapshot owner and separate passed reconciliation. An extended
catalog can then serve as `prior` for a later completed runtime preflight. The
new owner's plan must contain exactly that full catalog in `snapshot_reuse`.
The output retains every prior record, root, and owner association, plus a
canonical digest binding the inherited catalog to the new owner plan. It adds
only the new owner's physically stored blobs. Reused rows must equal the
deterministic prior-first selection; they cannot be relabelled as new owners.

The adapter reconstructs every original logical input and alias, all blob
descriptors, stored/reused maps, full directory memberships and typed byte
accounting. Every blob root must sit directly under an already counted evidence
owner. The selected path/inode sets are unique. Existing roots stay in the
monitor total; their allocation is never subtracted, moved, or estimated as
reclaimable space. The unchanged writer separately checks all current logical
bytes and complete gzip/logical EOF when measuring/writing a selected reference.
This catalog does not claim that reading the manifest alone decompresses gzip.

Production limits remain 1024 logical records, 64 MiB per file, 512 MiB logical,
128 MiB compressed and 4 MiB per manifest. Runtime callers retain 8 MiB document
and 32 MiB output reservation, the 256 MiB aggregate evidence cap, and all
original entry/live/floor and compiler namespace limits. No capacity fit is
claimed without an actual complete runtime selection and current measurement.

`test_catalog.py` uses only synthetic in-memory dictionaries and descriptors.
There are no filesystem fixtures, archived inputs, gzip calls, compiler/provider
calls, or subprocesses. Tests cover complete aliases and roots, compact and flat
input association, actual owner/audit/result binding, original-source presence,
stored/reused ownership, directory membership, inode identity, exact accounting,
and reservation types/bounds. These are proposed controls, not passed results.
