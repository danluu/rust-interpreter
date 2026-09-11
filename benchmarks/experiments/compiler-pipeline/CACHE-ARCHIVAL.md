# Preserve completed cache contents while making room for fresh histories

The fixed-tool warm comparisons are complete. Six independent large-project
cold histories remain required, with the original ordering and gates unchanged.
Nushell's latest fifteen-cycle history consumed roughly seventeen GiB on this
shared host. About ten GiB remained afterward. The first completed host-debug
target contains only 0.351 GiB of unique object inodes; removing more object
files alone is not a sufficient space plan for six new histories.

Prepare reversible compression of **exact completed task-owned public Cargo
targets**, with a separately reviewed inventory for each target. Start with a
completed public native target whose ownership, commands, source/bytecode
evidence and terminal state already verify. Do not infer ownership from size,
age or directory naming. Existing private caches, user-owned cleanup archives,
quarantine, sources and unrelated work remain outside scope. Installed tools
and the shared std-MIR sysroot also remain outside scope.

The archive must retain every file's bytes, mode, timestamp and hardlink group,
plus an inventory linking it to the original target and verified workflow.
Preserve query metadata and fingerprints; the allocation-history investigation
may need them. Benchmark reports, raw command records, source snapshots and
executed bytecode snapshots stay in place outside the retired Cargo target.

Qualification must precede real archival. Include hardlinks, executable and
non-executable files, empty files/directories, bounded path validation, corrupt
or missing archive members, changed source files, open files and interruption
before retirement. Verify extraction into an isolated owned fixture against
the complete original inventory. Restoring bytes is not proof of identical
future Cargo cache behavior or performance.

Under `.work/benchmark.lock`, revalidate provenance and closed files; write a
temporary archive in a new owned location with enough free space to finish it.
An incomplete archive must never authorize removing an original file. Decode
and hash every archived file against the inventory, verify the member set and
hardlink relationships, sync the completed archive, then recheck all originals
before retiring their paths. Journal progress and preserve both archive and
failure state on interruption. Never auto-resume a partial retirement or alter
another process to obtain an idle target. Publish the exact archive identity,
location, verified preservation and observed free-space change separately from
benchmark timing.

Initially qualify and archive one completed native target. Measure its actual
compression and remaining space before choosing further targets. Any extension
to independent-check or custom Cargo targets must first derive those exact
targets from the corresponding recorded commands, tool identities and unique
cache namespaces; prove that public-case ownership excludes private caches and
that all executed artifacts remain outside the retired cache. Do not accept an
arbitrary target path from the CLI.

Provide bounded inspection/restoration of archived files so future diagnostics
can read metadata without requiring a full cache rebuild. A restore must refuse
to overwrite a populated or unowned destination. Keep the archives local and
out of Git; commit the recipes, verification records and summaries. Compression
and retirement happen outside measured commands and never while a comparison
holds the lock. Do not lower the eight-GiB command guard, alter the cold sample
count or treat this logistical work as a compiler speedup.

Status: implemented by `scripts/archive_workflow_cache.py` and
`scripts/cache_archive.py`. [Qualification03](../../../results/cache-archive-qualification-03/assessment.md)
passes37 rejection checks, hardlink/mode/access/modification-time restoration
and four coordinator cases, including recovery after1,000 retired fixture paths.
The first real public native preparation refused Cargo root-directory xattrs
before any archive or retirement. Preserve that refusal; add and qualify exact
round-trip support for the two observed root markers before retrying. No real
cache has yet been retired by this mechanism.

The bounded format uses ZIP/DEFLATE payloads and a JSON manifest, storing each
inode's bytes once. It preserves regular-file/directory permission bits,
access/modification times and internal hardlink groups. It refuses special
files, external hardlinks, file flags and xattrs; inodes, ctimes, birth times and
ACLs are not recreated. ZIP entry names are never used as extraction paths.

Use a unique archive ID to prepare the exact completed workflow's native target:

```sh
python3 scripts/archive_workflow_cache.py --prepare ARCHIVE_ID --workflow COMPLETED_RUN
# Review the prepared inventory and ownership/closed-file evidence before applying.
python3 scripts/archive_workflow_cache.py --apply ARCHIVE_ID
python3 scripts/archive_workflow_cache.py --inspect ARCHIVE_ID --member RELATIVE_METADATA_PATH
python3 scripts/archive_workflow_cache.py --restore ARCHIVE_ID --restore-id UNIQUE_RESTORE_ID
```

Archives and reservations live under `.work/workflow-cache-archives`. Inspection
is limited to one MiB of output. Restoration creates a new directory beneath
the archive identity and refuses to overwrite existing files. Failed or partial
retirement reserves its original target and cannot be blindly retried under
another ID. Sources, reports and executed bytecode snapshots remain outside
the retired native target. No arbitrary target path is accepted by this CLI.
