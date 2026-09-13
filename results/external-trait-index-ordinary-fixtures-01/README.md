All 33 commands and 18 source/configuration states passed using the unchanged
owned Cmono compiler. The fixture source was restored. This validates ordinary
fixture behavior only: the proposed external-trait index was not compiled or
enabled, and these results make no performance claim.

The history covers nested trait reexports, a trait alias, equal associated
type/constant names, a macro-generated local trait, import edits (448 → 800 →
448), a Unicode source-position edit, cfg selection and an actual unused-import
warning. Five uncalled error states retain full raw compiler diagnostics:
missing method E0599, ambiguity E0034, type E0308, borrow E0382 and constant
evaluation E0080. Every error is followed by successful native compilation and
execution of restored source. In total, 13 native states compiled and ran.

The actual compiler key is
`f9fb3e5f59b8567fffd32c936a9864d0baee77038574236710fbcec75a57d33f`,
source commit `58e1e1f5311f4424ea81def4763081f6da62d9b3`.
Both existing CGU grouping options were explicitly disabled. The original
runner verified the complete compiler file hashes before and after the history,
checked installation stamps around each command, and guarded source/recipe
bytes. This archive binds the original copied helpers to those recorded hashes;
later PRIMARY helper changes do not replace the historical inputs.

`evidence.tar.gz` contains 239 verified members, 878,916 compressed bytes,
SHA-256 `6edf6d35d3d047a0114eaab69b163bcb4797b7234ab37120b660f95a3b4260d4`.
It includes all command/process receipts, raw stdout/stderr, each actual state
source, the frozen fixture/helper source snapshots, complete compiler readiness
identity, original supervisor evidence and the archive helper source.
`native-binary-hashes.json` retains the exact sizes and hashes of all 13 saved
native executables, the final restored executable and the native dependency.
Those binaries and incremental caches remain private and unchanged.

The archive independently rechecked the raw diagnostics, warning and native
outputs against all expected states, verified every source/output/binary hash,
then reread every compressed member and retained input. `summary.json`,
`members.json` and `inputs.json` record those checks; `archive-supervisor`
contains the archival process's own completed receipt. There were no failed
attempts in this fixture or archival history, and no files were retired.
