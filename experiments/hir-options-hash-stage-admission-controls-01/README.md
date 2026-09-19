# Hash-stage admission controls

Source-only proposal for nine in-memory controls. The unchanged bounded harness
from the completed prerequisite controls limits the test child to 120 seconds,
60 CPU seconds and 256 KiB per output, with no subprocesses, process signals or
network connections. Canonical admission remains 16/9/8 GiB.

These tests exercise four-required-audit rejection before dependency discovery,
explicit environment derivation, and import-alias restoration after an error.
They never discover providers, create a concrete hash-stage plan, run compilers,
or qualify actual native/run-make prerequisites. All nine controls passed once; actual raw evidence, independent verification and
the exact exercised source snapshots are retained in
`results/hir-options-hash-stage-admission-controls-01`. The later run-make result
binding additions are source-reviewed only and do not claim workload coverage.
