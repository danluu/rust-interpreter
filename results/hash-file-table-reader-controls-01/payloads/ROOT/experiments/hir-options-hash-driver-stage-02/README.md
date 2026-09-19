# Hash driver with a referenced frozen file table

This fresh stage succeeds the two preserved, failed preparations in
`hir-options-hash-driver-stage`. The first stopped on historical snapshot
ordering; the corrected reader passed 66 controls. The second passed that check
but exceeded the unchanged 256 MiB aggregate evidence reservation. Neither
preparation executed a compiler or driver.

The second preparation's later, closed projection reconstruction found
215,441,408 allocated evidence bytes and a 59,019,264-byte reservation: an excess
of 6,025,216 bytes. Its own duplicated input catalog accounted for 7,777,266
compressed bytes. These are retained diagnostic measurements, not build times.

The generic `frozen-file-table-delta-01` representation references an immutable
base file table and stores disjoint additions. The complete reconstructed
table's SHA-256, count and declared bytes must match. Every original file row,
link, absence, selected snapshot input and non-file header is retained. The base
catalog itself remains a selected, frozen input. Nested references, overlapping
rows, changed base data and indirect file routes are rejected.

`prepare.py` reconstructs the full table for discovery, guards and snapshot
selection. `stage.py` authenticates the exact base and tested helper before
reconstruction and requires the helper's actual 29-control qualification before
creating WORK. `verify.py` reconstructs the table independently, without
importing that helper, and still rehashes every input and provider inventory.
The launcher binds the compact representation to the reviewed packet.

The original three commands, role selection, prerequisite histories and
snapshot reuse rules are unchanged. Compiler admission remains 24/9/8 GiB;
read-only preparation remains 16/9/8 GiB. The namespace limit is 14 GiB and the
aggregate evidence limit is 256 MiB, with the existing remaining-stage reserve.
No storage fit or successful workload execution is assumed from source review.

This directory is currently source under qualification. Preparation, the three
hash workload commands, runtime installation and application timings remain
pending. No sub-0.5-second build result is established.
