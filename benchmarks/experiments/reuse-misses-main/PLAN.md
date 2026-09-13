# Integrate the qualified observer with published compiler-query reuse

The observer's original source is0b6770d, built asdbc221a2 and qualified with
83 exporter tests per profile,14 Python tests and44 fixture/project commands.
Origin/main subsequently includes2f98914's opt-in borrow-check query reuse.
Preserve that work. The only merge conflict is adjacent module declarations.

Build both exporter and wrapper from the combined committed source, retaining
the exact operation-map VM83ca5b78. The wrapper is allowed to differ from the
old control: its new enabled routing must be tested. Require88 exporter/routing
tests in each debug/release profile,14 reuse-harness tests,56 launcher tests,
and the published nine direct compiler plus one Cargo correctness suites using
the newly built binaries. Those tests cover the opt-in provider's verify/reuse
modes. No avoided-provider count is a speedup claim.

Then run a fresh28-command reuse-observer fixture and16-command fre history.
The fixture compares old control, new observer off and new observer on, with
strict uncalled errors, wrong edits, source restoration and option invalidation.
The fre history must match all retained bytecode/catalog digests and twelve
test outcomes across five valid edits. These use default borrow-cache off;
jointly enabling both diagnostics is not performance-qualified.

Serialize with the repository lock,45-second admission, two Cargo workers,
16GiB initial free space and8GiB per command. Record exact child identities,
binary/input hashes and every failure. Reuse no timing values from this run.
Only after correctness passes publish the integrated observer to main.
