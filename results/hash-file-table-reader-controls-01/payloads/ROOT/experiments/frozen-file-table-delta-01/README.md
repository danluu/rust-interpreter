# Frozen file table with one authenticated base

This is an unexecuted source proposal. It changes the representation of `files`
only. It does not reduce the reconstructed input set, select fewer snapshots,
change a resource cap, or establish workload qualification. Failed hash
preparations and their full catalogs remain unchanged.

`file_table.split(full_document, *, base_path, base_sha256, guard=...)` returns
an independent compact document. `file_table.expand(compact_document,
*, guard=...)` returns an independent full document. Both functions read one
ordinary base catalog, perform no writes, and invoke no child processes,
controllers, providers or compilers. The caller loads this exact source from
reviewed bytes, without relying on ambient import resolution or bytecode.

The compact document has two additional keys:

```json
{
  "file_table_base": {"path": "/absolute/pinned/inputs.json", "sha256": "64 lowercase hex digits"},
  "file_table_integrity": {"sha256": "canonical full files table SHA-256", "count": 109180, "total_bytes": 6770818566}
}
```

The numbers illustrate the preserved failed preparation02 table, not a new
prepared or qualified packet. `files` contains only paths disjoint from the
base table. Every other field, including complete `links`, `absent_paths`,
`snapshot_inputs`, environment, Python and plan binding, is copied without
changing JSON types or list order. `file_table_base` is distinct from native
reconciliation's broader `base_inputs` proof; the latter is never interpreted
by this helper.

The complete table digest is SHA-256 of UTF-8
`json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
allow_nan=False) + '\n'`. Integrity counters are exact integers, never booleans
or floats. Rows are exactly `{size, sha256, identity}`; identity is exactly
`{dev, ino, mode, size, mtime_ns, ctime_ns, nlink}` with integer fields and an
ordinary file mode. Different path aliases remain separate logical rows.

The splitter requires every base row in the full table with identical typed
JSON bytes. The expander rejects every overlap, even an equal row. Both require
the authenticated base document's own current file row to remain in the delta.
The base cannot contain either representation key or its own file row. This
single-level rule prevents recursive references and cycles. The base is read
through directory and file descriptors opened with `O_NOFOLLOW`; the route,
held file identity, named file identity, byte count and SHA-256 are checked.
The descriptors remain open through construction, followed by a final route and
identity check with no intervening callbacks before returning the new object.
Duplicate JSON keys, nonfinite values, changed or nonordinary bases are refused.

Finite constants are exposed in `file_table.py`: 180,000 files, 1 GiB per file,
8 GiB total declared file bytes, 64 MiB base JSON, 64 MiB canonical table and
64 MiB canonical document. JSON depth, node count and path lengths are bounded.
The capacity callback runs during reads and validation. Callers retain their
existing canonical admission, live floor, alarms, actual compact-document hash,
complete payload/link/absence rechecks and evidence accounting.

The returned full object removes only the two representation keys. Consumers
must retain the actual compact file's hash separately from the resolved object;
they must not pretend that the reconstructed JSON bytes are the on-disk file.
All selected snapshot records must be taken from the complete resolved table.
A publication must retain the compact document, pinned base document and every
selected proof payload according to the independently checked archive contract.

`test_file_table.py` uses only tiny task-owned catalog fixtures with synthetic
payload metadata. It covers complete reconstruction, aliases and type/order
preservation, no input/output aliasing, missing or changed base rows, overlapping
deltas, forged integrity, invalid identities and raw JSON, reference cycles,
symlink leaves/parents, read-time mutation, route replacement, finite bounds and
capacity refusal. These fixtures do not verify real provider payloads. The
source has not been imported or tested; a reviewed bounded harness and exact
packet approval are still required.
