//! Initialized backing storage with an independently bounded live guest prefix.
//!
//! Keeping spare bytes initialized permits a native call tree to reuse stable
//! storage. Dereferencing this type only exposes the active prefix; retained
//! bytes must never change ordinary guest bounds or live-memory accounting.
use std::ops::{Deref, DerefMut};

pub(crate) struct LinearMemory {
    initialized: Vec<u8>,
    // Invariant: active <= initialized.len(). Only methods below change it.
    active: usize,
}

impl From<Vec<u8>> for LinearMemory {
    fn from(initialized: Vec<u8>) -> Self {
        Self {
            active: initialized.len(),
            initialized,
        }
    }
}

impl FromIterator<u8> for LinearMemory {
    fn from_iter<T: IntoIterator<Item = u8>>(iter: T) -> Self {
        Vec::from_iter(iter).into()
    }
}

impl Deref for LinearMemory {
    type Target = [u8];
    #[inline(always)]
    fn deref(&self) -> &[u8] {
        // SAFETY: constructors and all mutations maintain the private active
        // prefix invariant. The allocation remains owned by this borrow.
        unsafe { self.initialized.get_unchecked(..self.active) }
    }
}

impl DerefMut for LinearMemory {
    #[inline(always)]
    fn deref_mut(&mut self) -> &mut [u8] {
        // SAFETY: the same prefix invariant holds; &mut self is exclusive and
        // no safe slice operation can change either vector length or active.
        unsafe { self.initialized.get_unchecked_mut(..self.active) }
    }
}

impl LinearMemory {
    /// Vec::resize semantics for the live prefix, including reinitialization
    /// after truncation. Do not zero the old live prefix or fill new bytes twice.
    pub(crate) fn resize(&mut self, end: usize, value: u8) {
        if end > self.active {
            let retained_end = end.min(self.initialized.len());
            if end > self.initialized.len() {
                self.initialized.resize(end, value);
            }
            self.initialized[self.active..retained_end].fill(value);
        }
        self.active = end;
    }

    #[inline]
    pub(crate) fn truncate(&mut self, end: usize) {
        self.active = self.active.min(end);
    }

    /// Prepare initialized storage without exposing it to guest accesses.
    /// Callers must do this outside generated execution and impose an explicit
    /// speculative-storage bound. Allocation failure is an optimization decline.
    pub(crate) fn prepare(&mut self, end: usize) -> Result<(), std::collections::TryReserveError> {
        if end > self.initialized.len() {
            self.initialized.try_reserve(end - self.initialized.len())?;
            self.initialized.resize(end, 0);
        }
        Ok(())
    }

    pub(crate) fn initialized_len(&self) -> usize {
        self.initialized.len()
    }

    /// Raw access to initialized backing, including retained non-live bytes.
    /// A native caller must still enforce its separate guest live extent.
    pub(crate) fn prepared_mut_ptr(&mut self) -> *mut u8 {
        self.initialized.as_mut_ptr()
    }

    /// Commit a native call tree's final prefix after checking its cursor.
    /// All elements are initialized, but callers must separately establish the
    /// guest initialization/copy semantics for any newly visible range.
    pub(crate) fn commit_native_len(&mut self, end: usize) -> Result<(), String> {
        if end > self.initialized.len() {
            return Err("native call returned an invalid guest memory length".into());
        }
        self.active = end;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Memory, heap};

    fn memory(limit: usize) -> Memory {
        Memory {
            bytes: vec![0x57; 17].into(),
            heap: heap::Heap::default(),
            limit,
            readonly_end: 16,
            peak: 17,
            auxiliary_bytes: 0,
        }
    }

    #[test]
    fn prepared_bytes_do_not_change_guest_bounds_or_live_budget() {
        let mut m = memory(128);
        let total = m.total_len();
        let budget = m.heap_budget(16);
        m.bytes.prepare(4096).unwrap();
        assert_eq!(m.bytes.initialized_len(), 4096);
        assert_eq!(m.bytes.len(), 17);
        assert_eq!(m.total_len(), total);
        assert_eq!(m.heap_budget(16), budget);
        assert_eq!(m.peak, 17);
        assert_eq!(m.load(16, 1).unwrap(), 0x57);
        for size in [1, 8, 16] {
            assert!(m.load(17, size).is_err());
            assert!(m.store(17, size, 0x99).is_err());
            assert!(m.copy(16, 17, size).is_err());
        }
        assert_eq!(m.load(usize::MAX, 0).unwrap(), 0);
        assert!(m.store(15, 1, 1).unwrap_err().contains("read-only"));
    }

    #[test]
    fn reused_frames_zero_padding_and_stale_bytes_without_moving_prepared_storage() {
        let mut m = memory(4096);
        m.bytes.prepare(1024).unwrap();
        let pointer = m.bytes.as_ptr();
        let first = m.reserve_frame(31, 64).unwrap();
        assert_eq!(first, 64);
        assert!(m.bytes[17..95].iter().all(|&b| b == 0));
        m.fill(first, 0xcd, 31).unwrap();
        m.bytes.truncate(first); // Return keeps the padding before the callee.
        assert_eq!(m.bytes.len(), 64);
        assert_eq!(m.load(63, 1).unwrap(), 0);
        assert!(m.load(64, 1).is_err());
        let second = m.reserve_frame(7, 16).unwrap();
        assert_eq!(second, 64);
        assert_eq!(&m.bytes[second..], &[0; 7]);
        assert_eq!(m.bytes[16], 0x57);
        assert_eq!(m.bytes.as_ptr(), pointer);
        assert_eq!(m.peak, 95);
        m.bytes.truncate(second);
        m.reserve_frame(48, 16).unwrap();
        assert!(m.bytes[64..112].iter().all(|&b| b == 0));
        assert_eq!(m.bytes.as_ptr(), pointer);
    }

    #[test]
    fn prepared_capacity_does_not_bypass_frame_limit_or_publish_a_bad_native_cursor() {
        let mut m = memory(63);
        m.bytes.prepare(4096).unwrap();
        assert_eq!(
            m.reserve_frame(1, 64).unwrap_err(),
            "interpreter memory limit exceeded"
        );
        assert_eq!(m.bytes.len(), 17);
        assert_eq!(m.peak, 17);
        assert!(m.bytes.commit_native_len(4097).is_err());
        assert_eq!(m.bytes.len(), 17);
        m.bytes.commit_native_len(32).unwrap();
        assert_eq!(m.bytes.len(), 32);
        assert_eq!(&m.bytes[17..], &[0; 15]);
    }

    #[test]
    fn active_resize_matches_vector_semantics_through_growth_shrink_and_reuse() {
        let mut reference = vec![7; 5];
        let mut actual: LinearMemory = reference.clone().into();
        for (end, byte, prepare) in [
            (100, 9, 200),
            (3, 1, 0),
            (50, 8, 500),
            (0, 2, 0),
            (17, 3, 20),
            (900, 4, 0),
            (901, 5, 2048),
        ] {
            actual.prepare(prepare).unwrap();
            actual.resize(end, byte);
            reference.resize(end, byte);
            assert_eq!(&*actual, reference);
            actual.truncate(end.saturating_sub(2));
            reference.truncate(end.saturating_sub(2));
            assert_eq!(&*actual, reference);
        }
    }

    #[test]
    fn impossible_preparation_leaves_the_existing_prefix_usable() {
        let mut bytes: LinearMemory = vec![1, 2, 3].into();
        let pointer = bytes.as_ptr();
        assert!(bytes.prepare(usize::MAX).is_err());
        assert_eq!(&*bytes, &[1, 2, 3]);
        assert_eq!(bytes.as_ptr(), pointer);
        bytes.resize(4, 9);
        assert_eq!(&*bytes, &[1, 2, 3, 9]);
    }
}
