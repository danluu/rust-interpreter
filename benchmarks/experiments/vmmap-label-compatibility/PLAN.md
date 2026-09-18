# Recognize the retained owned arena on this macOS host

The first fresh block guest passed, but twelve successful vmmap inspections
reported its executable arena as `Untagged`. The old `VM_ALLOCATE`-only parser
never admitted sampling. Preserve that complete failure and leave its exhaustive
successor unstarted. This is a diagnostic-format fix, not a guest runtime change
or a new timing attempt for the rejected composition.

Share one parser between capture readiness and summary. Require the exact VM PID
header, either observed anonymous-region label, complete address bounds and
`rwx/rwx` permissions. Reject invalid or overlapping ranges. Attribution still
requires the captured process's emitted-code map and exact arena containment;
an anonymous executable mapping alone does not identify a guest instruction.

Run the full Python contracts, the nine existing scalar-attribution controls
against the changed summary dependency, and replay all twelve retained current
reports plus the two earlier successful native maps. In each real report,
require the parsed interval to contain that process's independent emitted-code
range. Keep process identity, liveness, original assertions and no-signal policy.
These checks execute no guest and claim no speedup. Use the shared lock,
12 GiB initial admission and an 8 GiB floor. Record all source and report hashes.

After qualification, collect fresh diagnostic windows under new02 namespaces.
Never relabel the zero-window01 attempt as successful or repeat its completed
execution merely because later analysis waited for the shared lock.
