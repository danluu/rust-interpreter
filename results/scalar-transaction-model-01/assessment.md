# Compilation stopped before model execution

The first source-frozen command failed to compile. The test-only memory snapshot
destructor prevents moving the heap vector out of three existing test assertions.
No model control or census ran. Preserve this closed failure; use cloned vectors
in those assertions and start a separately named attempt.
