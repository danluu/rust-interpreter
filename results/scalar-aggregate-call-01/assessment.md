# Snapshot observer exposed three test-only move incompatibilities

The first debug compilation failed before any control ran. The restored test-only
`Memory` Drop observer prevents moving its heap Vec out of three existing test
assertions (two byte-comparison assertions and one CPU-query assertion). Change
those assertions to clone the compared heap bytes, as their linear-byte side
already does. This does not change production memory behavior.

The failed command, diagnostics and source f09e88e6 are closed. Continue under a
fresh run name after the test-only fix; no correctness or timing result is claimed
for this run. [Closure](closure.json).
