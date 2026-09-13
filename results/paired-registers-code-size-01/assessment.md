# Generated size on unprofiled qualification artifacts

Read-only comparison of the seven completed wide/paired qualification pairs
finds smaller generated code in every pair: 1.24% and 1.20% for the two token
tests, 2.24% for folded, and 0.16–0.20% for four short pgrust cases. Each pair
uses identical arguments and selections, with matching logical instructions,
memory and entropy. No new guest process was run.

These are the saved qualification artifacts and unprofiled generated sizes.
The separate current three-test profile comparison includes instrumentation.
Neither static size comparison establishes dynamic retired instructions or
complete-command latency; the frozen edited-command comparison is active.
