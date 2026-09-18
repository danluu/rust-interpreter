# Explicit runtime readmission after a device-identity change

Prepared, not executed. A read-only September 18 check found E's `bin/rustc`
changed from device 16777231 to 16777229 while its inode, mode, size, nanosecond
mtime/ctime and hard-link count remained identical. That observation covers only
one file. It does not establish equivalence of the complete components.

Historical metadata03, the original E source preflight and the unexecuted R01
proposal remain unchanged. R01's exact historical component guards would reject
the current device identity, so R01 must not be launched as prepared.

This separate controller admits the original specification again under the
canonical lock. It records complete new component snapshots and every changed
stamp. Readmission permits only the explicit historical-device/current-device
pair while requiring every other stamp field and every inventory member to
match. Any additional difference fails and retains the observation for review.
It then hashes all 3,709 component files / 650,879,912 logical bytes against the
original admitted digests. This conditional comparison is confined to admission;
every subsequent barrier compares all seven fields of the exact new snapshots.

The 28 ordered children repeat five Git source guards, one SDK-tool selection,
eleven loader inspections, three E compiler identity/option probes, two raw E0080
source probes, five Git source guards and the final SDK-tool selection. All source,
backtrace, bootstrap configuration, native runtime and provider bytes remain
subject to the existing full checks. Final component hashes and exact stamps
must pass before the new metadata/source receipts are written.

Success produces new `metadata.json`, `components-and-stamps.json` and a passed
source-preflight `receipt.json`. The original candidate is copied byte-for-byte.
A later R02 installation proposal must bind these fresh receipts and exact current
snapshots; no ready record or runtime installation is produced here. The historical
source preflight is a predecessor, not the new run's result.

Launch uses 600 seconds of canonical-lock admission and a fresh 10 GiB free-space
check. The original owned supervisor retains its 9 GiB active-child stop and
8 GiB floor. Retained source inputs are bounded to 64 MiB, with 128 MiB reserved
for outputs and filesystem metadata. No B2/pthread admission policy changes,
cleanup, retries or unrelated process control are included.
