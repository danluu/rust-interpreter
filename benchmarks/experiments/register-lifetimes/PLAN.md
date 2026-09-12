# Allocate virtual-register storage by lifetime

The latest pointer-promotion screen improved complete token commands by 0.34%,
so that compiler stays parked. Current hot functions still declare hundreds or
thousands of distinct 128-bit virtual-register slots. The JIT can retain only
three of those identities in native pairs across regions.

Investigate assigning the same virtual slot to different values with disjoint
lifetimes. The old parked `virtual-register-compaction-01` only removed gaps in
numbering and explicitly preserved every distinct referenced identity. This is
a different, many-to-one allocation proof; do not rerun that old candidate or
mix pointer promotion, register-width packing or larger caches into this one.

Start with an offline typed census. Reuse the existing bounded full-CFG
register liveness and exhaustive operand visitor. Derive conservative closed
intervals containing all live-in points, reads and writes of each identity.
Include dead writes, unreachable blocks, backedges and initial-zero reads.
Calls read their argument/result addresses and cannot access caller register
storage. Preserve full 128-bit values; use no sampled-value or alias assumptions.
Assign a slot only when its prior interval ends strictly before the next begins.
Certify every reused interval and retain the original function on any bound or
proof decline. Account for the analysis and certificate work and memory.

Report old/referenced/allocated slots, bounds/declines and per-function
reductions. Match any profile by function index and full code/shape, including
duplicate rendered names. Estimate how allocation changes the existing native
residency choices using original operation counters; disclose that this is
logical coverage, not measured machine cost. Saved inputs remain immutable.

Only useful measured coverage justifies integration. A candidate must remap
every register operand exhaustively after existing inlining/control-flow
decisions, preserving operation order, PCs, function IDs, frame/argument/result
layouts, data and all runtime checks. Keep the VM and bytecode version unchanged.
Qualify independent execution on joins, loops, initial-zero uses, dead writes,
aliased multi-output operations, wide values, calls, faults and exact budgets.
Include deterministic generated valid programs and original Rust tests in
both interpreter and custom JIT modes.

Before promotion, use one predeclared source-edit screen with native, retained
and candidate commands on the complete twelve-test token module, followed by
separate folded and pgrust guards only if the primary passes. Require at least
10% paired token wall improvement with no CPU regression. Failed candidates
stay parked without retiming. Broad large-project qualification follows only
after the fixed screen passes.

Use the shared lock with a 45-second wait, two build workers and at least 8 GiB
free before children. Preserve unrelated workloads, private data, installed
tools and raw evidence. Checking stays strict and guest execution remains our
own interpreter/direct AArch64 JIT.
