# Guest Call transaction model

This qualification hook exists only in bytecode library unit-test builds on
macOS AArch64. A scoped thread-local test flag selects it; production builds
contain neither the modules nor the hook. Do not expose or benchmark this Rust
callback path as the proposed native-to-native fast path. It exists to compare
the transaction with the actual ordinary VM over complete programs.

The hook is after original direct/indirect target validation and the caller's
original Call instruction/profile debit, before frame reservation. Remaining
budget covers the whole bounded acyclic leaf. Guards establish valid original
memory/working/depth limits and preexisting input/result ranges. All inputs are
captured in ABI order; aliases into new payload/padding decline. Read-only or
invalid results decline even when a callee might fault first: ordinary fallback
retains the original error order. Missing metadata rejects before mutation.

Prepare at most one leaf frame plus alignment padding outside native execution.
Initialized backing may move/grow, but no guest-visible prefix, pointer bits,
active registers/frames, peak or logical counter changes on decline. The custom
native leaf writes only private output/scratch. Its failure discards all private
work and proceeds with the original Call body. Compiled-code cache bookkeeping
is private; cap this model at 64 mappings of 256 KiB, 16 MiB total.

Success validates private steps/profile, zeroes only newly retained padding,
stores the result to its prechecked destination, and updates peak memory to the
original callee payload end including heap/auxiliary bytes. Original physical
callee frame/register backing is dead after Return; future reservations retain
ordinary reinitialization. Profiled model runs use one-instruction native ranges
in otherwise ordinary interpreter dispatch. Mixing the model with normal JIT
execution or partial-validation artifacts explicitly rejects.

Six focused controls compare complete program results, instruction counts,
logical per-PC profiles and peak memory, including all selected budget/memory/
depth tails, overlapping argument/result slots, new-frame argument reads,
result padding/payload aliases, escaped Local addresses observed by future
calls, assertions/traps before invalid results, indirect signatures, metadata/
code admission, and unchanged visible memory on decline. Run debug/release,
then the full workspace regressions. Freeze source and retain failures; use
the existing two-worker, shared-lock and conservative disk admission rules.

Still pending: native caller register/cursor preservation and success commit,
direct branch linkage, shared-arena admission, precise production profile
publication, strict/Cargo fixtures, original real workload assertion checks,
and the frozen primary/full edited-source performance gates. The test-only
bridge provides no performance conclusion.
