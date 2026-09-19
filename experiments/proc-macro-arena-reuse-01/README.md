# Bounded proc-macro symbol arena reuse

This unapplied prototype targets source commit
`4de35bdacef0e3cd18a66bc30b5459c19e09b118`. No compiler source, package or
qualified artifact was changed. No compilation, tests, profiles or benchmarks
have run for this patch.

The client calls `Symbol::invalidate_all` before decoding each macro invocation
and after encoding its response. `Interner::clear` advances the symbol base,
clears its name and string tables, then currently replaces its arena. That
replacement drops every byte chunk and the vector holding the chunks. The next
nonempty symbol needs a fresh chunk of at least 4096 bytes.

`arena-reuse.patch` introduces `Arena::reset`. It retains at most one existing
ordinary 4096-byte chunk in a separate optional field, resets its allocation
cursor, and drops every other chunk and the entire chunk vector allocation.
An oversized first allocation is released completely. Reset performs no new
allocation. Repeated resets of an unused arena leave it unallocated. Subsequent
growth still doubles the last active chunk as before, including when that chunk
is the retained page.

The only production change in `symbol.rs` calls this reset in place of arena
replacement. Symbol-base advancement, saturation, overflow handling, name/hash
and string/vector clearing are unchanged. Both tables are cleared before any
arena storage becomes reusable. Reset takes `&mut self`; the normal borrow
contract forbids live arena references at that point. The interner's internal
extended-lifetime references are erased by its existing table-clearing order.
Byte alignment and the actual allocation/write routines are unchanged. No
symbol, token, span, macro result or external dependency is reused semantically.

The retained chunk lives until the client interner's thread-local state is
dropped. The cap is **per client interner**, not per process. A cold or forced
cross-thread client may gain nothing. This changes client-side `proc_macro`
code: changing only the compiler server does not establish that existing macro
dylibs execute it. Any future experiment must identify/rebuild the actual
clients and preserve the original compiler/package identities.

The seven tests embedded in `patched/arena.rs` exercise the actual allocator:
empty and zero-length reset, pointer/cursor reuse, multiple-chunk and vector
capacity release, oversized-first rejection, growth after reuse, live Unicode
contents, and reset after a caught unwind. `arena_unit_tests.rs` includes that
exact file for a future standalone test build. It requires a compiler/library
supporting the original source's APIs; no compatibility shim or allocator model
is substituted.

Three additional tests embedded in `patched/symbol.rs` exercise the actual
interner's duplicate IDs, stale-symbol rejection, double clear, oversized
Unicode strings, and its existing overflow/nonpanicking-clear boundary. These
need the real proc-macro crate context; the standalone arena file does not run
them. All ten tests are source only. Their presence is not qualification of
reset, unwinding, nested clients or real macro side effects.

The saved Ruff candidate summary records 2396 `expand_proc_macro` events and
0.524015090 seconds in that label. `expand_crate` has 1.066426 seconds inclusive
and 0.453275446 seconds self time. These labels do not isolate allocator work,
and their overlap is not a saving estimate. The baseline is a single separately
observed compiler run, not a balanced performance comparison. The exact saved
summary references and source assessment are recorded in `source-review.json`.

Existing warm RPC buffers already retain capacity, normal same-thread dispatch
already calls directly, and panic-hook installation already uses `Once`.
Cross-stage C-ABI serialization and nested-client isolation remain unchanged.
The earlier span-handle lookup proposal is independent of this patch.

Before adoption, independently review the patch and compile the actual tests,
then qualify real macro clients for output/spans/diagnostics, panic and nesting
behavior, and ordered external effects. A later measurement would need allocator
attribution and process memory as well as end-to-end time. The current saved
evidence establishes a concrete allocation pattern; it does not establish a
performance benefit or justify a compiler rebuild ahead of current work.
