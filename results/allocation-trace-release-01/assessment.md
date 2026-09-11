# Allocation trace release qualification

All 272 workspace tests pass in release, one existing ignored; frozen inputs
remain unchanged. Supervisor 85729/controller 85733 finished successfully and
installed source `9bd66cd` as tool `e965f566ac6ba4f8e5f6f174af1258e305b5b0d2acde24017581616fe33f2a06`. The Git-backed build index reproduces
that source key and verifies its installed binaries.

The exporter is `65c11a7d2aacc2941266f3ae9fc90805177a5d82174a4a90d0704e634cba9ad2`. The VM
remains `60b00d7d` and the lightweight wrapper remains `ba366dd3`, byte-identical
to their previous installed copies. This adds an opt-in compiler diagnostic;
no guest-runtime or default-setting change is included.

See [test/install receipt](summary.json), [Git source index](../../benchmarks/tool-builds.json)
and [original-fixture qualification](../allocation-trace-fixtures-01/assessment.md).
