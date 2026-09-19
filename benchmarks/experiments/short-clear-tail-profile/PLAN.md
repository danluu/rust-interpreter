# Exact original guest qualification of short clear tails

After the closed workspace continuation (609 tests in both profiles), run five
original assertions: the two current ES8 integration tests, token block and
exhaustive semantics, and folded-literal differential semantics. Bind artifacts
and catalogs from closed ES8 and current-host token/folded captures.

For each case run the unchanged adopted VM once in entropy record mode, then
the candidate once in replay mode. Use the already qualified entropy library.
This avoids attributing host feature changes or random hash seeds to the JIT.
Require original success, identical per-PC logical counts, memory and entropy,
all other non-timing/non-byte VM counters, and zero JIT declines. Reuse the
qualified operation-map observer to reconstruct and validate each process's
code independently. Check matched function/region/span identities and exact
20-byte growth for every replacement of the old 40-byte helper by the 60-byte
helper; require all old helpers gone in candidate code. Do not demand native
byte equality: instruction branches and scalar entry addresses move.

Ten guest commands, no compilation or source edit. Record every child's identity,
logs, profiles and maps before checking outcomes so a reporting failure never
requires replaying a successful guest. Freeze all sources, tools, controllers,
proofs, and input artifacts until terminal status and independent closure.
Current profiles are correctness evidence only, not latency measurements.

Shared lock admission45s, initial12GiB, each guest8GiB. Own new raw outputs only;
no cleanup, process control, default tool replacement or new billing. Keep strict
checking: subsequent explicit composition reuses the byte-identical qualified
frontend and its121 controls, then fresh type/borrow negative probes in the ES8
changed-source screen. The prospective ES8 and held-out gates remain unchanged.
