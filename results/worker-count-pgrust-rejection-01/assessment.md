# First worker qualification rejected before compilation

The harness rejected identical tool keys even though worker counts differed.
The attempt ended with status2 before creating its project run directory; no
benchmark samples were produced. The failed receipt is preserved. The guard
now includes worker counts, and two real CLI probes verify identical-setting
rejection and passage to an exclusive pre-build directory sentinel. Original
source and sentinel contents remain unchanged. Retry uses a new run identity.

[Failure evidence](summary.json), [guard qualification](../worker-count-harness-02/summary.json).
