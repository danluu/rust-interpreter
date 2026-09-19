# Historical input record audit successor

This is an unrun saved-evidence reader successor. The frozen stage02 verifier
`cbff690675b8697855bb87b0e09d9b77495fc0b8968855301e1a88612ec62a3f`
and its complete prepared packet remain unchanged. The original reader failed
before any driver workload while accessing a nonexistent `size` member in a
historical `sha256`/`stamp` record.

`verify.py` pins `HERE` to the original stage02 source. Its pure
`canonical_inherited_record(row)` accepts exactly two observed JSON schemas:

- `sha256` plus the seven-integer list `stamp`, ordered as device, inode, mode,
  size, mtime, ctime, link count.
- `sha256`, integer `size`, and the exact seven-field integer `identity` object.

Both normalize to the latter form, rejecting unknown or mixed schemas, boolean
or floating-point identities, malformed digests, nonordinary files, inconsistent
size, invalid identities and payloads over the existing 1 GiB per-file limit.
The current complete frozen row must already have the canonical schema.
`inherited_inputs` compares the whole normalized SHA, size and identity with
typed JSON equality. Existing plan, link, absence and exact one-level native
reconciliation-base checks remain in place.

The independent compact-file-table reader and its qualified 22-control behavior
are byte/AST unchanged. The original prepared verifier remains authenticated as
the exact frozen input and is named explicitly in the eventual report.
This external auditor is authenticated separately by its reviewed source/control
proof and execution wrapper; it does not claim membership in the old freeze.
The report's `verifier_sha256` identifies the actual executing successor.

`test_inherited_records.py` contains 22 pure fixture methods. It uses in-memory
catalogs and mocked read/hash/frozen boundaries; no provider file is opened.
Two copied metadata examples come from O's retained read-only census
`.work/hash-driver-inherited-input-wire-schema-assessment-01.json`, SHA
`6aaf27fce56c2878e1c9c48bac9e13091ec08c398a2438eb059a41aa5f0c98d5`.
That census reports 1,039 compiler and 166 run-make stamp records, with no
normalized mismatch against the complete current frozen rows. The fixtures
qualify only the adapter and do not constitute actual provider qualification.

No imports, fixture controls, packet preparation, audit execution or driver
workload have been performed for this successor at source handoff.
