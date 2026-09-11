Repeated executed snapshots have identical complete file contents. Preserve
every evidence path while sharing their data through independent APFS clones.
This is maintenance outside benchmark timers, not a guest allocation or cache
identity optimization.

Apple documents that [clonefile](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/clonefile.2)
shares data blocks while subsequent writes remain independent. Its ownership
and ACL exceptions matter: this helper accepts only owned plain files and plain
destination directories, rejecting attributes, ACLs, flags and special modes.
It restores and verifies permissions and mtime, ownership and exact SHA-256.
Inode, ctime and birth time change; reads can change access time. There is no
hardlink or ordinary-copy fallback.

The [owned-fixture qualification](../../../results/artifact-clones-qualification-01/summary.json)
passes independent writes in both directions, differing source/destination
permissions, preserved mtime and 18 rejection checks. Injected cloning and
publication failures preserve both original files and remove the owned temporary.

The coordinator derives paths and hashes exclusively from completed public
workflow records, reruns their verifier, checks closed snapshot directories and
open files, and records an exact inventory before application. Commit the
reviewed inventory identity before applying. It revalidates the whole inventory
before replacing any files, journals replacements, and reruns original workflow
and metadata checks afterward. Failed/partial application cannot be blindly
retried. Retain raw inventories and journals under `.work/clones`.

The first pilot covers 42 snapshots from the completed public native-controls
token workflow: 29 duplicate files (835,639,023 logical bytes). No private or
unrelated snapshots are eligible. Logical duplicate bytes are not an exact
physical-space saving; volume snapshots and concurrent work can affect storage.
