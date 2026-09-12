# Explicit Cargo integration targets: fixture passes

The new launcher passes 14 actual Cargo/native/custom commands: five native
controls and nine interpreter/JIT commands. Source is ordinary Git code at
`3d3dfb6`, branch `experiment/test-targets`; exporter, wrapper and VM remain the
retained `9637b0ac` build.

Two integration targets deliberately give different outcomes for the same
entry name. A succeeds, B fails its assertion, and A succeeds again. The default
library-test route still succeeds. A wrong production edit fails natively and
in the JIT. Uncalled type and borrow errors are rejected by rustc (E0308/E0502)
without returning stale guest results; restoring source succeeds again.
Four target-selection unit checks also pass. All processes are terminal,
source restoration and all 28 output-stream hashes verify.

This is target-routing correctness on an isolated package. It does not yet
qualify the 52 original fre integration tests or establish a performance win.
The current selector uses a separate Cargo namespace per integration target;
sharing compatible dependency builds across target selections is a next design
question, with artifact binding and invocation locking preserved.

The summary's native/custom counts were corrected from hard-coded 6/8 to the
actual 5/9 records. No command outcome or timing changed. The exact executed
driver and original controller summary remain under the raw run directory;
future drivers derive these counts from records.
