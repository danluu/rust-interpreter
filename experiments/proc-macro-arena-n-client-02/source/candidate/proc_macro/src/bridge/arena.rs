//! A minimal arena allocator inspired by `rustc_arena::DroplessArena`.
//!
//! This is unfortunately a minimal re-implementation rather than a dependency
//! as it is difficult to depend on crates from within `proc_macro`, due to it
//! being built at the same time as `std`.

use std::cell::{Cell, RefCell};
use std::mem::MaybeUninit;
use std::ops::Range;
use std::{cmp, ptr, slice};

// Keep the original growth page size when selecting a retained chunk.
const RETAINED_PAGE: usize = 4096;

/// A minimal arena allocator inspired by `rustc_arena::DroplessArena`.
///
/// This is unfortunately a complete re-implementation rather than a dependency
/// as it is difficult to depend on crates from within `proc_macro`, due to it
/// being built at the same time as `std`.
///
/// This arena doesn't have support for allocating anything other than byte
/// slices, as that is all that is necessary.
pub(crate) struct Arena {
    start: Cell<*mut MaybeUninit<u8>>,
    end: Cell<*mut MaybeUninit<u8>>,
    chunks: RefCell<Vec<Box<[MaybeUninit<u8>]>>>,
    // Read growth metadata without borrowing bytes containing live allocations.
    chunk_capacity: Cell<usize>,
}

impl Arena {
    pub(crate) fn new() -> Self {
        Arena {
            start: Cell::new(ptr::null_mut()),
            end: Cell::new(ptr::null_mut()),
            chunks: RefCell::new(Vec::new()),
            chunk_capacity: Cell::new(0),
        }
    }

    /// Invalidate all allocations, retaining only a first ordinary page.
    ///
    /// Callers storing extended-lifetime references must clear them before
    /// reset. Shrinking the ownership vector may reallocate and is best-effort;
    /// its capacity is not guaranteed to become exactly one.
    pub(crate) fn reset(&mut self) {
        self.chunk_capacity.set(0);
        self.start.set(ptr::null_mut());
        self.end.set(ptr::null_mut());

        let chunks = self.chunks.get_mut();
        if chunks.first().is_some_and(|chunk| chunk.len() == RETAINED_PAGE) {
            chunks.truncate(1);
            if chunks.capacity() > 1 {
                chunks.shrink_to_fit();
            }
            // Derive fresh cursors after any movement of the ownership vector.
            let Range { start, end } = chunks[0].as_mut_ptr_range();
            self.start.set(start);
            self.end.set(end);
            self.chunk_capacity.set(RETAINED_PAGE);
        } else {
            // An oversized first request retains neither its bytes nor vector.
            *chunks = Vec::new();
        }
    }

    /// Add a new chunk with at least `additional` free bytes.
    #[inline(never)]
    #[cold]
    fn grow(&self, additional: usize) {
        // The arenas start with PAGE-sized chunks, and then each new chunk is twice as
        // big as its predecessor, up until we reach HUGE_PAGE-sized chunks, whereupon
        // we stop growing. This scales well, from arenas that are barely used up to
        // arenas that are used for 100s of MiBs. Note also that the chosen sizes match
        // the usual sizes of pages and huge pages on Linux.
        const PAGE: usize = 4096;
        const HUGE_PAGE: usize =
            cfg_select! {
                any(target_pointer_width = "64", target_pointer_width = "32") => 2 * 1024 * 1024,
                _ => 8192, // just make it compile for -Zbuild-std
            };

        let mut chunks = self.chunks.borrow_mut();
        let previous_capacity = self.chunk_capacity.get();
        let mut new_cap;
        if previous_capacity != 0 {
            // If the previous chunk's len is less than HUGE_PAGE
            // bytes, then this chunk will be least double the previous
            // chunk's size.
            new_cap = previous_capacity.min(HUGE_PAGE / 2);
            new_cap *= 2;
        } else {
            new_cap = PAGE;
        }
        // Also ensure that this chunk can fit `additional`.
        new_cap = cmp::max(additional, new_cap);

        let chunk = chunks.push_mut(Box::new_uninit_slice(new_cap));
        let Range { start, end } = chunk.as_mut_ptr_range();
        self.start.set(start);
        self.end.set(end);
        self.chunk_capacity.set(new_cap);
    }

    /// Allocates a byte slice with specified size from the current memory
    /// chunk. Returns `None` if there is no free space left to satisfy the
    /// request.
    #[allow(clippy::mut_from_ref)]
    fn alloc_raw_without_grow(&self, bytes: usize) -> Option<&mut [MaybeUninit<u8>]> {
        let start = self.start.get().addr();
        let old_end = self.end.get();
        let end = old_end.addr();

        let new_end = end.checked_sub(bytes)?;
        if start <= new_end {
            let new_end = old_end.with_addr(new_end);
            self.end.set(new_end);
            // SAFETY: `bytes` bytes starting at `new_end` were just reserved.
            Some(unsafe { slice::from_raw_parts_mut(new_end, bytes) })
        } else {
            None
        }
    }

    fn alloc_raw(&self, bytes: usize) -> &mut [MaybeUninit<u8>] {
        if bytes == 0 {
            return &mut [];
        }

        if let Some(a) = self.alloc_raw_without_grow(bytes) {
            return a;
        }
        // No free space left. Allocate a new chunk to satisfy the request.
        // On failure the grow will panic or abort.
        self.grow(bytes);
        self.alloc_raw_without_grow(bytes).unwrap()
    }

    #[allow(clippy::mut_from_ref)] // arena allocator
    pub(crate) fn alloc_str<'a>(&'a self, string: &str) -> &'a mut str {
        let alloc = self.alloc_raw(string.len());
        let bytes = alloc.write_copy_of_slice(string.as_bytes());

        // SAFETY: we convert from `&str` to `&[u8]`, clone it into the arena,
        // and immediately convert the clone back to `&str`.
        unsafe { str::from_utf8_unchecked_mut(bytes) }
    }
}

#[cfg(test)]
mod reuse_tests {
    use super::{Arena, RETAINED_PAGE as PAGE};

    fn assert_reset_storage(arena: &Arena, retains_page: bool) {
        let chunks = arena.chunks.borrow();
        if retains_page {
            assert_eq!(chunks.len(), 1);
            assert_eq!(chunks[0].len(), PAGE);
            // Vec::shrink_to_fit may retain capacity above its length.
            assert!(chunks.capacity() >= 1);
            let range = chunks[0].as_ptr_range();
            assert_eq!(arena.start.get().cast_const(), range.start);
            assert_eq!(arena.end.get().cast_const(), range.end);
        } else {
            assert!(chunks.is_empty());
            assert_eq!(chunks.capacity(), 0);
            assert!(arena.start.get().is_null());
            assert!(arena.end.get().is_null());
        }
    }

    #[test]
    fn empty_and_zero_length_reset_stay_unallocated() {
        let mut arena = Arena::new();
        assert_eq!(arena.alloc_str(""), "");
        arena.reset();
        assert_reset_storage(&arena, false);
        arena.reset();
        assert_reset_storage(&arena, false);
    }

    #[test]
    fn ordinary_page_and_cursor_are_reused() {
        let mut arena = Arena::new();
        let first = arena.alloc_str("first").as_ptr();
        arena.reset();
        assert_reset_storage(&arena, true);
        let next = arena.alloc_str("other");
        assert_eq!(next, "other");
        assert_eq!(next.as_ptr(), first);
        arena.reset();
        assert_reset_storage(&arena, true);
    }

    #[test]
    fn multiple_chunks_are_released_and_vector_shrink_is_best_effort() {
        let mut arena = Arena::new();
        arena.alloc_str(&"a".repeat(PAGE));
        arena.alloc_str(&"b".repeat(PAGE * 2 + 17));
        arena.alloc_str(&"c".repeat(PAGE * 4 + 35));
        assert_eq!(arena.chunks.borrow().len(), 3);
        assert!(arena.chunks.borrow().capacity() >= 3);
        arena.reset();
        assert_reset_storage(&arena, true);
    }

    #[test]
    fn oversized_first_chunk_is_not_retained() {
        let mut arena = Arena::new();
        arena.alloc_str(&"x".repeat(PAGE + 1));
        assert_eq!(arena.chunks.borrow()[0].len(), PAGE + 1);
        arena.reset();
        assert_reset_storage(&arena, false);
        arena.alloc_str("small");
        arena.reset();
        assert_reset_storage(&arena, true);
    }

    #[test]
    fn growth_after_reuse_preserves_doubling_and_releases_extra() {
        let mut arena = Arena::new();
        arena.alloc_str("seed");
        arena.reset();
        arena.alloc_str(&"a".repeat(PAGE));
        assert_eq!(arena.chunks.borrow().len(), 1);
        arena.alloc_str("b");
        assert_eq!(arena.chunks.borrow()[1].len(), PAGE * 2);
        arena.alloc_str(&"c".repeat(PAGE * 3));
        assert_eq!(arena.chunks.borrow()[2].len(), PAGE * 4);
        arena.reset();
        assert_reset_storage(&arena, true);
    }

    #[test]
    fn unicode_and_live_allocations_keep_exact_contents() {
        let mut arena = Arena::new();
        arena.alloc_str("seed");
        arena.reset();
        let first: &str = arena.alloc_str("alpha_β_雪");
        let second: &str = arena.alloc_str("☃".repeat(PAGE).as_str());
        assert_eq!(first, "alpha_β_雪");
        assert_eq!(second, "☃".repeat(PAGE));
        assert_eq!(first, "alpha_β_雪");
    }

    #[test]
    fn retained_disjoint_mutable_strings_survive_shared_growth() {
        let mut arena = Arena::new();
        arena.alloc_str("seed");
        arena.reset();
        let shared = &arena;
        let first = shared.alloc_str("first");
        let second = shared.alloc_str("second");
        first.make_ascii_uppercase();
        second.make_ascii_uppercase();
        let large = shared.alloc_str(&"x".repeat(PAGE * 2));
        large.make_ascii_uppercase();
        assert_eq!(first, "FIRST");
        assert_eq!(second, "SECOND");
        first.make_ascii_lowercase();
        assert_eq!(first, "first");
        assert_eq!(large, "X".repeat(PAGE * 2).as_str());
    }

    #[inline(never)]
    fn move_arena(arena: Arena) -> Arena {
        arena
    }

    #[test]
    fn populated_arena_move_preserves_reuse_reset_and_growth() {
        let mut arena = Arena::new();
        arena.alloc_str("seed");
        arena.reset();
        let arena = move_arena(arena);
        assert_eq!(arena.alloc_str("after move"), "after move");

        // Also move with a partially consumed retained page, before resetting.
        let mut arena = move_arena(arena);
        assert_eq!(arena.alloc_str("after another move"), "after another move");
        arena.reset();
        let mut arena = move_arena(arena);
        let first: &str = arena.alloc_str("left");
        let large: &str = arena.alloc_str(&"r".repeat(PAGE * 3));
        assert_eq!(first, "left");
        assert_eq!(large.len(), PAGE * 3);
        assert!(large.bytes().all(|byte| byte == b'r'));
        assert_eq!(first, "left");
        arena.reset();
        assert_reset_storage(&arena, true);
        assert_eq!(arena.alloc_str("final reuse"), "final reuse");
    }

    #[test]
    fn reset_after_caught_unwind_reuses_storage() {
        let mut arena = Arena::new();
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            arena.alloc_str("before panic");
            panic!("fixture panic");
        }));
        assert!(result.is_err());
        arena.reset();
        assert_reset_storage(&arena, true);
        assert_eq!(arena.alloc_str("after panic"), "after panic");
    }

    #[test]
    fn recorded_capacity_tracks_empty_growth_retention_and_oversized_reset() {
        let mut arena = Arena::new();
        assert_eq!(arena.chunk_capacity.get(), 0);
        arena.alloc_str("");
        assert_eq!(arena.chunk_capacity.get(), 0);
        arena.alloc_str("seed");
        assert_eq!(arena.chunk_capacity.get(), PAGE);
        arena.reset();
        assert_eq!(arena.chunk_capacity.get(), PAGE);
        arena.alloc_str(&"a".repeat(PAGE));
        assert_eq!(arena.chunk_capacity.get(), PAGE);
        arena.alloc_str("b");
        assert_eq!(arena.chunk_capacity.get(), PAGE * 2);
        arena.alloc_str(&"c".repeat(PAGE * 4 + 19));
        assert_eq!(arena.chunk_capacity.get(), PAGE * 4 + 19);
        arena.reset();
        assert_eq!(arena.chunk_capacity.get(), PAGE);

        let mut oversized = Arena::new();
        oversized.alloc_str(&"x".repeat(PAGE + 1));
        assert_eq!(oversized.chunk_capacity.get(), PAGE + 1);
        oversized.reset();
        assert_eq!(oversized.chunk_capacity.get(), 0);
        oversized.alloc_str("");
        assert_eq!(oversized.chunk_capacity.get(), 0);
        oversized.alloc_str("small");
        assert_eq!(oversized.chunk_capacity.get(), PAGE);
    }
}
