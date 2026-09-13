# Count fully overwritten local writes within exact native regions

The constant-memory initialization proof covers only 16 / 20 saved clearing
samples; defer runtime clear elision. Earlier narrow-register packing and local
metadata transfer diagnostics are negative. The existing small-memory partition
has 436 / 243 data-transfer samples, all at ordinary widths. It does not support
prioritizing odd-width assembly. No unchanged candidate is retimed.

Measure a different hypothesis: local Store, Copy or constant FillBytes bytes
may be completely overwritten before any observation. Use typed bytecode and
the exact saved native region boundaries. Start every region with unknown
register facts. Track only explicit Local, literals and bounded unsigned-64-bit
Local-plus-literal addresses, killing every output via the authoritative visitor.
Do not seed whole-function facts or infer pointees from names or types.

Track each pending write byte separately. A known local read observes only
pending bytes in its exact range. Copy reads before writing. Unknown accesses,
possibly failing arithmetic, assertions, unsupported effects and region ends
make every outstanding write observable. A candidate is fully overwritten only
when no original byte remains, with no earlier read or fault barrier. Decline
on resource exhaustion. Require allocated-frame ranges and exact constant sizes;
no heap/static elision, partial-width rewrite or cross-region optimization.

Qualify the diagnostic with partial-overwrite, alias, copy-order, fault-barrier,
integer-width, join-boundary and resource-limit controls. Independently enumerate
four-event byte-memory histories and compare all observed reads, barrier memory
snapshots and final bytes after removing the reported writes. The diagnostic
does not execute generated code or change the interpreter, exporter or artifact.

Join candidates to the existing same-process sampled PCs and exact profiles.
Report whole-operation and transfer-only sample coverage separately, including
emitter-elided sites and conservative declines. Counts are not speedup estimates.
Only substantial coverage warrants an emitter prototype, which still needs
fault/budget/state qualification and real source-edit/build/test comparisons.

Keep the existing pinned toolchain and unchanged bytecode dependency. Build with
two Cargo workers under the shared lock (45-second admission), 16 GiB initial
headroom and 8 GiB per child; saved analyses need 12 GiB. Freeze source, artifact,
map, profile and prior proof identities. Preserve failures, the paused goal,
other sessions, private data and installed/shared tools. No subagents or AWS.
