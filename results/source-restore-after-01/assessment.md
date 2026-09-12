# Source restoration now invalidates Cargo's edited artifact

`SourceEdit` refreshes the staged original's modification time immediately
before renaming it back. The native regression now rebuilds and passes the
restored original with the identical Cargo command and no manual touch. Its
original/wrong/restored sequence contains three real Cargo commands.

Three focused Python tests check fresh restoration, preservation of the backup
when metadata publication fails, and preservation of external edits. All 18
root Python tests pass. A normal root-launcher fre integration command also
rebuilt the restored production source and passed its three original assertions.
The final root probe is recorded under `.work/integration-root-route-01`.

The fresh original-source artifact still differs from an earlier original-source
artifact. Fixing stale reuse therefore does not resolve the separate export
determinism question. The earlier stale probe and both regression phases remain
available; no historical measurement was relabelled.
