# Tree-aware native samples

The shared-cursor primary fails its wall gate: 1.70% improvement versus 4.1545%
A/A, CPU improvement 0.10%. Do not retime the source or start larger histories.
Capture two bounded three-second diagnostic windows, one original block test
and one original exhaustive test, using immutable tool a984e603 / VM 2c20261d.
No runtime or benchmark workload changes. These are perturbed partial windows,
not latency measurements or substitutes for the failed end-to-end result.

Extend experiment-local copies of the owned-PID sampler and attribution tools
to admit the explicit bridge option. No operation map or instruction profiler:
the existing same-process dump partitions ordinary entries and complete trees.
Keep identity, parentage, cwd, live arena, same-PID code bytes and file hashes
verified. Let every owned bounded execution finish; never signal another process.

Classify x20 Frame accesses only in ordinary entries: inside trees x20 is a
return destination. Preserve exact clear/copy sequence recognition within each
entry (including tree bulk clears), classify tree budget subtraction and direct
cursor-field memory instructions, and leave every other word unclassified.
Reconcile all generated/unresolved self-PC samples. Counts are not retired
instructions, cycles, or predicted speedups. Function names are descriptive.

Qualify option rejection/forwarding, ABI-aware classes, partition failures,
sequence boundaries and budget operands before sampling. Bind all frozen source,
qualified build/profile/closure, original artifact/catalog and diagnostic outputs.
Two workers remain unchanged; hold the shared benchmark lock for each execution
and offline attribution with a45-second wait. Require12 GiB before setup and
8 GiB before each child. No new native compilation or guest benchmark history.
