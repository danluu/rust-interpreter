//! A minimal arena allocator inspired by `rustc_arena::DroplessArena`.
//!
//! This is unfortunately a minimal re-implementation rather than a dependency
//! as it is difficult to depend on crates from within `proc_macro`, due to it
//! being built at the same time as `std`.

use std::cell::{Cell, RefCell};
use std::mem::MaybeUninit;
use std::ops::Range;
use std::{cmp, ptr, slice};

const PAGE: usize = 4096;

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
    // Both active and retained allocation owners remain behind UnsafeCell.
    // alloc_str writes through the cursor under &self, as in the original arena.
    storage: RefCell<Storage>,
}

struct Storage {
    chunks: Vec<Box<[MaybeUninit<u8>]>>,
    // At most one ordinary page survives reset; oversized chunks never do.
    retained_chunk: Option<Box<[MaybeUninit<u8>]>>,
}

impl Arena {
    pub(crate) fn new() -> Self {
        Arena {
            start: Cell::new(ptr::null_mut()),
            end: Cell::new(ptr::null_mut()),
            storage: RefCell::new(Storage { chunks: Vec::new(), retained_chunk: None }),
        }
    }

    /// Invalidate all allocations, retaining at most one ordinary page.
    ///
    /// The mutable borrow prevents outstanding arena borrows. Callers storing
    /// extended-lifetime references must clear those references before reset.
    /// No allocation is performed, including when resetting an empty arena.
    pub(crate) fn reset(&mut self) {
        self.start.set(ptr::null_mut());
        self.end.set(ptr::null_mut());

        // Take the vector so its allocation is released as well as its chunks.
        // The retained page lives separately and needs no vector allocation.
        let storage = self.storage.get_mut();
        let mut chunks = std::mem::take(&mut storage.chunks);
        if storage.retained_chunk.is_none()
            && chunks.first().is_some_and(|chunk| chunk.len() == PAGE)
        {
            storage.retained_chunk = Some(chunks.swap_remove(0));
        }
        drop(chunks);

        if let Some(chunk) = storage.retained_chunk.as_mut() {
            let Range { start, end } = chunk.as_mut_ptr_range();
            self.start.set(start);
            self.end.set(end);
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
        const HUGE_PAGE: usize =
            cfg_select! {
                any(target_pointer_width = "64", target_pointer_width = "32") => 2 * 1024 * 1024,
                _ => 8192, // just make it compile for -Zbuild-std
            };

        let mut storage = self.storage.borrow_mut();
        let mut new_cap;
        if let Some(last_chunk) = storage.chunks.last_mut() {
            // If the previous chunk's len is less than HUGE_PAGE
            // bytes, then this chunk will be least double the previous
            // chunk's size.
            new_cap = last_chunk.len().min(HUGE_PAGE / 2);
            new_cap *= 2;
        } else if storage.retained_chunk.is_some() {
            // Its capacity is PAGE by construction. Inspect only the option tag;
            // do not borrow the retained slice while earlier allocations live.
            new_cap = PAGE * 2;
        } else {
            new_cap = PAGE;
        }
        // Also ensure that this chunk can fit `additional`.
        new_cap = cmp::max(additional, new_cap);

        let chunk = storage.chunks.push_mut(Box::new_uninit_slice(new_cap));
        let Range { start, end } = chunk.as_mut_ptr_range();
        self.start.set(start);
        self.end.set(end);
        // End the temporary storage borrow before alloc_raw writes via cursor.
        drop(storage);
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
    use super::{Arena, PAGE};

    fn assert_reset_storage(arena: &Arena, retains_page: bool) {
        let storage = arena.storage.borrow();
        let chunks = &storage.chunks;
        assert!(chunks.is_empty());
        assert_eq!(chunks.capacity(), 0);
        assert_eq!(storage.retained_chunk.as_ref().map(|c| c.len()), retains_page.then_some(PAGE));
        if let Some(chunk) = &storage.retained_chunk {
            let range = chunk.as_ptr_range();
            assert_eq!(arena.start.get().cast_const(), range.start);
            assert_eq!(arena.end.get().cast_const(), range.end);
        } else {
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
    fn multiple_chunks_and_vector_capacity_are_released() {
        let mut arena = Arena::new();
        arena.alloc_str(&"a".repeat(PAGE));
        arena.alloc_str(&"b".repeat(PAGE * 2 + 17));
        arena.alloc_str(&"c".repeat(PAGE * 4 + 35));
        assert_eq!(arena.storage.borrow().chunks.len(), 3);
        assert!(arena.storage.borrow().chunks.capacity() >= 3);
        arena.reset();
        assert_reset_storage(&arena, true);
    }

    #[test]
    fn oversized_first_chunk_is_not_retained() {
        let mut arena = Arena::new();
        arena.alloc_str(&"x".repeat(PAGE + 1));
        assert_eq!(arena.storage.borrow().chunks[0].len(), PAGE + 1);
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
        assert!(arena.storage.borrow().chunks.is_empty());
        arena.alloc_str("b");
        assert_eq!(arena.storage.borrow().chunks[0].len(), PAGE * 2);
        arena.alloc_str(&"c".repeat(PAGE * 3));
        assert_eq!(arena.storage.borrow().chunks[1].len(), PAGE * 4);
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
}
