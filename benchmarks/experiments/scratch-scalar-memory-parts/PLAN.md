# Partition current emitted memory costs

The two new adopted-VM captures still attribute many generated self samples to
Copy and Load operations. Reconstruct their exact same-process emission using
the existing memory-part observer, then separate address formation, bounds,
register traffic and payload movement. No guest executes in this analysis and
no native code is published.

Use the exact adopted Rust sources and ROOT-only shared target. Reuse the four
Rust observer contracts in the unchanged 608-test build and the two unchanged
Python boundary/ambiguity contracts; verify source/record equality. Run only
the two previously ignored saved-capture reconstructions and the attribution.
Require byte-for-byte complete function and scalar-body reconstruction, a
complete disjoint memory partition and exact sample accounting against each
closed coarse report. Keep unresolved/host samples and all observer limits.

Serialize with the benchmark lock. Use two Cargo jobs, nonincremental host
builds, existing release debug settings and conservative initial admission of
max(14 GiB, 8 GiB + twice the allocated shared target), then an 8 GiB child floor.
Never clean the shared target or touch another session's processes or files.
These observations support a next-mechanism decision, not a speedup estimate.
