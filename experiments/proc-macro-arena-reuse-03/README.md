# Proc-macro arena reuse with the original ownership layout

This is an unapplied source proposal against compiler commit
`4de35bdacef0e3cd18a66bc30b5459c19e09b118`. It has not been compiled, tested,
benchmarked or applied to the frozen compiler. It supersedes version 02, which
is preserved with a new status note about unresolved provenance when moving its
directly owned retained box. Version 01 remains rejected because that box was
outside the interior-mutability boundary. No predecessor should be executed.

The arena retains its original `RefCell<Vec<Box<[MaybeUninit<u8>]>>>` layout.
Reset requires `&mut Arena`, clears both cursors first, then retains only a
first 4096-byte chunk. It drops all additional chunks, requests best-effort
vector shrinking when capacity exceeds one, and derives fresh cursors afterward.
An empty arena or an oversized first chunk instead gets a new empty vector.
The retention bound is one ordinary page of allocation bytes; vector ownership
capacity is best-effort and has no portable exact-one-slot guarantee. Shrinking
can reallocate. This version makes no allocation-free-reset promise.

Keeping the box owners in the original vector avoids introducing a direct box
field whose move through an arena value would need a new provenance argument.
The original `grow`, `alloc_raw_without_grow`, `alloc_raw` and `alloc_str`
functions are byte-identical, including their pointer, alignment and UTF-8
operations. No unsafe block or unchecked API is added. The interner still
advances its symbol base and clears both symbol tables before calling reset;
its duplicate, saturation and overflow behavior is unchanged.

The [Rust Reference](https://doc.rust-lang.org/reference/behavior-considered-undefined.html#undefined.immutable)
describes shared-reference immutability through owned boxes, and the
[UnsafeCell rules](https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html#aliasing-rules)
describe the interior-mutability boundary without relaxing live-reference
requirements. Preserving the original representation and operations reduces
the new reasoning required; it is not a completed soundness proof.

`original/` holds exact source copies; `patched/` holds the proposed actual
code. `arena-reuse.patch` is relative to the compiler and
`from-superseded-02.diff` records the correction. `arena_unit_tests.rs` includes
the real patched arena for a future standalone test build, with no model or
compatibility shim. Its nine tests cover empty and oversized reset, page and
cursor reuse, additional-chunk release, growth, Unicode, disjoint mutable
strings across growth, caught unwind, and populated-arena movement through a
non-inlined value-returning function before reuse, reset and growth. They do
not assert that best-effort shrinking produces capacity one. Three additional
interner tests need the actual proc-macro crate context and are not included
in that standalone wrapper. All twelve tests are currently source only.

The installed 2026-09-08 nightly metadata identifies Rust 1.100.0-nightly. Its
installed source marks all APIs used here stable, so no feature gate is added.
Miri is not installed. No toolchain install or update is part of this proposal.
Ordinary unit tests would check behavior but would not establish aliasing-model
soundness or an end-to-end compiler performance benefit.

The saved Ruff profile has 2396 candidate `expand_proc_macro` calls totaling
0.524015090 seconds, including macro code and bridge work. Overlapping expansion
labels are not additive, and those summaries do not attribute allocator cost.
Any benefit remains unmeasured. A future compiler experiment must identify
rebuilt macro clients using this implementation; changing only the compiler
server would not demonstrate that they use the patch. No semantic results,
tokens, spans, external effects or ABI behavior are cached or bypassed.
