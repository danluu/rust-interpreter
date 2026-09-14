# Cached continuations and fixed ABI snapshots

Start from adopted runtime df4006e0, with all prior failed compositions retained.
Ordinary register elimination covers only 26/1,561 and 18/1,231 current generated
self samples after memory-effect modeling; leave it unimplemented. Native
Return dispatch retains 27/16 samples. Current typed result-copy samples are
14/58, including 27 exhaustive samples for 136-byte returns and 24 for 304-byte
returns. These are partial, perturbed windows, not predicted speedups.

The older continuation census found every executed native Call had a compiled
next-PC target, but deferred a cache because of Call-side costs. Prototype that
cache together with a materially different fixed copy strategy. The prior failed
boundary bundle used directional pair loops above 128 bytes and wider clears.
This experiment keeps clearing and register transfers at the adopted baseline.

1. Add an initialized host-only u32 continuation field in the existing 48-byte
   Frame. Native Calls store a relocated arena-relative byte offset only when
   their exact next-PC resume entry exists. Zero means use the current table
   lookup; every VM/TLS/root frame initializes zero. Never read padding. Keep
   logical PC, result address, all guest storage and publication semantics.
   Relocate only unpublished staged words, validate targets/units/ranges, and
   preserve code-budget refusal. The owning JIT arena never moves or rewrites
   published code during a guest execution. Do not serialize/reuse offsets
   across arenas or tests. Return restores the parent and reloads its assigned
   pairs through the existing resume entry. All faults, TLS, missing targets,
   unsupported successors, one-past continuations and zero-progress exits keep
   their original behavior. Account for added Call stores and fallback work.
2. For complete ABI copies of 129 through 384 bytes, load the full source before
   any destination write, using only caller-saved v0-v7 and v16-v31. Preserve
   v8-v15, x16 callee target, x17 register cursor, x22 budget and all persistent
   pairs. Keep exact scalar tails and unaligned accesses; no overread, padding
   exposure or reordering between arguments. Larger copies retain the existing
   implementation. This is a bounded snapshot, with no overlap-direction branch.

Qualify emission/relocation without execution first, independently check new
words with the host assembler, then compare complete bytes, overlap directions,
all alignments, tails and ABI canaries. Exercise nested native/VM/TLS frames,
dirty descriptor reuse, skipped/missing continuations, profile modes, arena
limits and every instruction-budget prefix. Reconstruct diagnostic code maps
after applying exactly the same relocations. Record failures without repeating
successful commands merely to fix reporting.

Then run debug/release workspace controls, strict/cache/error fixtures and the
three exact original profiles. Keep compiler/exporter/wrapper bytes equal to
df4006e0. Freeze one primary-first 40-command changed-source token screen, with
the existing A/A and regression gates, before timing. A failed gate parks this
composition without an unchanged rerun or larger history. Passing requires the
full five-project comparison and both parser guards before adoption.

Use the shared lock and two build/test workers; admission is at least 14 GiB or
8 GiB plus twice allocated shared target size, with an 8 GiB child floor. Keep
the shared build target, paused goal, suggestions, peer worktrees and independent
cleaner intact. No subagents, foreign guest backend or new service activation.
