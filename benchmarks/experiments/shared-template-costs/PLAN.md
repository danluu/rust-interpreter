# Preparation audit of the failed shared-template primary

Read all15valid edited custom receipts from the closed32-command comparison:
five baseline, five A/A duplicate and five candidate. Keep original mode/tool
identities, changed-source checks, test outcomes and worker assignments. Add no
guest, compiler build, artifact decoding or new latency sample.

The seven established preparation controls and three new sharing controls check
overlapping timers, cumulative versus delta counters, source/tool/mode scope,
numeric bounds and separately reported shared-store construction. Preserve
every per-state result and compare descriptive medians by mode. Sum compiler
intervals within each owner; final code/function counters are cumulative and
must not be summed across tests. Template hits/bytes are invocation deltas.

Shared-store construction is a distinct interval before worker construction.
Owner construction and compilation intervals overlap between workers. None of
these sums or differences are CPU, critical-path savings or a causal explanation
of the failed gate. Separate medians are not additive. Use the audit to decide
whether a finer diagnostic or a materially changed mechanism is justified.

Serialize with the root lock,45-second admission,12GiB initial/8GiB child floor.
Freeze the exact checked runtime sources, original comparison/qualification
receipts and observer sources. Preserve failures and successful controls before
correction; do not rerun the original workloads for bookkeeping.
