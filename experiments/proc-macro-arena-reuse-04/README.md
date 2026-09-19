# Proc-macro arena reuse: avoid reading live chunk bytes for capacity

This source-only, unapplied successor addresses the observed Arena03 Stacked
Borrows failure. The saved diagnostic at
`../../results/proc-macro-arena-miri-04/stacked-borrows.stderr` identifies the
previous chunk's `last_chunk.len()` as introducing a shared slice over bytes
containing live mutable strings. That line came from the unchanged original
growth implementation. A focused original-source control is pending; this
proposal does not preempt its result or claim that native unit success proves
aliasing-model correctness. Arena03's native pass and Miri failure are both
preserved, with a new `MIRI-STATUS.md` stating that it is not adoptable.

The allocation owners stay in `RefCell<Vec<Box<[MaybeUninit<u8>]>>>`. A private
`Cell<usize>` records the capacity of the current chunk. It starts at zero,
becomes the newly allocated capacity after growth sets both cursors, and is
cleared before reset changes ownership. When reset keeps a first ordinary
4096-byte page, it restores that capacity only after truncation, best-effort
vector shrinking and cursor reacquisition. Empty and oversized-first resets
leave it zero. Growth uses this integer for the existing doubling and maximum
size calculations, without obtaining a reference into an older chunk.

No unsafe block or unchecked API is added. The original three allocation/write
functions are byte-identical. Symbol invalidation, table clearing and the
interner source/tests are unchanged from Arena03. Reset keeps at most one
ordinary page and no oversized chunk. Vector shrinking remains best-effort,
can reallocate, and has no portable exact-one-slot capacity guarantee.

All nine Arena03 test functions are preserved byte-for-byte. One additional
test checks capacity metadata across empty allocation, initial allocation,
retained-page exhaustion, doubling, an oversized subsequent request, retained
reset, oversized-first reset, and reuse afterward. The separate three real
Interner tests are also unchanged. `arena_unit_tests.rs` includes the actual
Arena and ten tests, with no model. The full proc-macro crate would include
thirteen proposed tests. No version04 compilation, tests, Miri run, benchmark,
compiler rebuild, provider import or installed-toolchain change has occurred.

`original/` contains the exact compiler sources at commit
`4de35bdacef0e3cd18a66bc30b5459c19e09b118`; `patched/` contains this proposal.
`arena-reuse.patch` is relative to those originals and
`from-miri-failed-03.diff` records the narrow successor change. The existing
[Rust Reference](https://doc.rust-lang.org/reference/behavior-considered-undefined.html#undefined.immutable)
and [UnsafeCell](https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html#aliasing-rules)
constraints continue to apply. Removing one observed shared-slice creation is
a targeted correction, not a blanket soundness or performance claim.
