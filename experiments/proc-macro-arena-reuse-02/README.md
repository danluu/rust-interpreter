# Proc-macro arena reuse: interior-mutability correction

This is an unapplied, uncompiled successor against compiler source
`4de35bdacef0e3cd18a66bc30b5459c19e09b118`. The original `proc-macro-arena-reuse-01`
prototype is **rejected for its retained-storage representation**, not merely
untested. Its original eight files are preserved; a new `STATUS.md` records the
rejection. No version has been compiled or run, and no compiler source or
qualified package changed.

The predecessor put the retained `Option<Box<[MaybeUninit<u8>]>>` directly in
`Arena`. That left its bytes outside the original interior-mutability boundary
while `alloc_str(&self)` writes through cursor pointers. Shared-reference
immutability extends through owned boxes, so this representation is not an
acceptable basis for those writes. `RefCell` uses `UnsafeCell`, but that does
not excuse conflicting live references. These constraints follow from the
[Rust Reference](https://doc.rust-lang.org/reference/behavior-considered-undefined.html#undefined.immutable)
and [UnsafeCell aliasing rules](https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html#aliasing-rules).

The successor puts `chunks` and `retained_chunk` in a single private `Storage`
inside `RefCell<Storage>`. Reset still takes `&mut Arena` and accesses storage
with safe `get_mut`. It invalidates both cursors before dropping chunks, keeps
at most one ordinary 4096-byte chunk, frees every oversized/additional chunk and
the chunk vector allocation, then restores the retained page's cursors. Reset
allocates nothing. The interner still clears its symbol tables before reset;
its base advancement, duplicate handling, saturation and overflow paths are
unchanged.

Growth temporarily borrows storage mutably. It uses the retained option's tag
and known page size rather than making a shared slice reference into a page
whose earlier allocations may still be live. After constructing the next chunk
and recording its cursors, it explicitly drops the temporary `RefMut` before
the existing allocation/write path resumes. No new unchecked API or unsafe
block was introduced. The original byte-allocation, bounds, alignment and UTF-8
write routines are byte-identical. This restores the intended storage boundary;
it is a source argument awaiting independent review, not a completed soundness
or performance qualification.

`arena-reuse.patch` is relative to the untouched compiler files.
`from-rejected-01.diff` records only the successor delta. `original/` contains
exact compiler copies, and `patched/` contains the proposed actual code.
`arena_unit_tests.rs` includes the actual patched arena for a future standalone
test build; it substitutes no model or compatibility shim.

Eight embedded arena tests cover empty reset, bounded retention, pointer/cursor
reuse, oversized release, vector capacity release, growth, Unicode contents,
and unwind recovery. The new case keeps two disjoint mutable strings live
through writes and shared-arena growth, then reads and mutates them again. It
is intended to exercise the retained allocation path under an aliasing checker
as well as ordinary execution; it has not been run. The three unchanged tests
in `patched/symbol.rs` exercise the actual interner and require the real
proc-macro crate context. All eleven tests remain source only.

The retention cap is per client interner, including only one 4096-byte chunk
and fixed ownership metadata after reset. Fresh or forced cross-thread clients
may gain nothing. Actual macro clients must use a rebuilt, identified
`proc_macro` implementation; changing only the compiler server is insufficient.
Macro results, tokens, spans, dependencies, external effects and the C ABI are
not cached or bypassed.

Saved Ruff summaries still provide no allocator attribution: 2396 candidate
`expand_proc_macro` calls take 0.524015090 seconds, including macro user code
and bridge work. Expansion labels overlap and are not added into a saving
estimate. No new workload, profile, provider import, holdout or benchmark was
run. The opportunity remains unmeasured and does not take priority over the
current runtime work.
