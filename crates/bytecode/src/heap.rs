//! Guest allocations with reusable ranges. Addresses are offsets, not pointers.
use std::collections::BTreeMap;

pub(crate) const TAG: usize = crate::HEAP_POINTER_TAG as usize;

pub(crate) struct Heap {
    pub bytes: Vec<u8>,
    allocations: BTreeMap<usize, (usize, usize)>,
    free: BTreeMap<usize, usize>,
    static_len: usize,
    allocation_limit: usize,
}

impl Default for Heap {
    fn default() -> Self {
        Self {
            bytes: Vec::new(),
            allocations: BTreeMap::new(),
            free: BTreeMap::new(),
            static_len: 0,
            allocation_limit: crate::DEFAULT_ALLOCATION_LIMIT,
        }
    }
}

impl Heap {
    pub fn with_statics(bytes: &[u8], allocation_limit: usize) -> Self {
        Self {
            bytes: bytes.to_vec(),
            static_len: bytes.len(),
            allocation_limit,
            ..Self::default()
        }
    }
    pub(super) fn owned_layout(&self, offset: usize) -> Option<(usize, usize)> {
        self.allocations.get(&offset).copied()
    }
    fn layout(size: usize, align: usize) -> Result<(), String> {
        if size == 0 || !align.is_power_of_two() || align > TAG {
            return Err("invalid guest allocation layout".into());
        }
        Ok(())
    }

    pub fn allocate(
        &mut self,
        size: usize,
        align: usize,
        budget: usize,
        zeroed: bool,
    ) -> Result<usize, String> {
        Self::layout(size, align)?;
        if self.allocations.len() >= self.allocation_limit || self.bytes.len() > budget {
            return Ok(0);
        }
        let aligned = |value: usize| value.checked_add(align - 1).map(|v| v & !(align - 1));
        let reusable = self.free.iter().find_map(|(&base, &len)| {
            let start = aligned(base)?;
            let end = start.checked_add(size)?;
            (end <= base + len).then_some((base, len, start, end))
        });
        let (start, end) = if let Some((base, len, start, end)) = reusable {
            self.free.remove(&base);
            if start > base {
                self.free.insert(base, start - base);
            }
            if end < base + len {
                self.free.insert(end, base + len - end);
            }
            (start, end)
        } else {
            let old_end = self.bytes.len().max(16);
            let Some(start) = aligned(old_end) else {
                return Ok(0);
            };
            let Some(end) = start.checked_add(size) else {
                return Ok(0);
            };
            if end > budget || end >= TAG {
                return Ok(0);
            }
            self.bytes.resize(end, 0);
            if start > old_end {
                self.free.insert(old_end, start - old_end);
            }
            (start, end)
        };
        if zeroed {
            self.bytes[start..end].fill(0);
        }
        self.allocations.insert(start, (size, align));
        Ok(TAG + start)
    }

    fn allocation(&self, pointer: usize, size: usize, align: usize) -> Result<usize, String> {
        Self::layout(size, align)?;
        let start = pointer
            .checked_sub(TAG)
            .ok_or("invalid guest allocation pointer")?;
        if self.allocations.get(&start) != Some(&(size, align)) {
            return Err("guest allocation pointer or layout mismatch".into());
        }
        Ok(start)
    }

    fn release_range(&mut self, mut start: usize, mut size: usize) {
        if let Some((&previous, &len)) = self.free.range(..start).next_back() {
            if previous + len == start {
                self.free.remove(&previous);
                start = previous;
                size += len;
            }
        }
        if let Some(len) = self.free.remove(&(start + size)) {
            size += len;
        }
        if start + size == self.bytes.len() {
            self.bytes.truncate(start);
        } else {
            self.free.insert(start, size);
        }
        if self.allocations.is_empty() {
            self.bytes.truncate(self.static_len);
            self.free.clear();
        }
    }

    pub fn deallocate(&mut self, pointer: usize, size: usize, align: usize) -> Result<(), String> {
        let start = self.allocation(pointer, size, align)?;
        self.allocations.remove(&start);
        self.release_range(start, size);
        Ok(())
    }

    pub fn reallocate(
        &mut self,
        pointer: usize,
        old_size: usize,
        align: usize,
        new_size: usize,
        budget: usize,
    ) -> Result<usize, String> {
        Self::layout(new_size, align)?;
        let start = self.allocation(pointer, old_size, align)?;
        if old_size == new_size {
            return Ok(pointer);
        }
        if new_size < old_size {
            self.allocations.insert(start, (new_size, align));
            self.release_range(start + new_size, old_size - new_size);
            return Ok(pointer);
        }
        let old_end = start + old_size;
        if let Some(end) = start.checked_add(new_size) {
            if old_end == self.bytes.len() && end <= budget && end < TAG {
                self.bytes.resize(end, 0);
                self.allocations.insert(start, (new_size, align));
                return Ok(pointer);
            }
            if let Some(&len) = self.free.get(&old_end) {
                let growth = new_size - old_size;
                if len >= growth {
                    self.free.remove(&old_end);
                    if len > growth {
                        self.free.insert(end, len - growth);
                    }
                    self.allocations.insert(start, (new_size, align));
                    return Ok(pointer);
                }
            }
        }
        let replacement = self.allocate(new_size, align, budget, false)?;
        if replacement == 0 {
            return Ok(0);
        } // Original remains allocated.
        self.bytes.copy_within(start..old_end, replacement - TAG);
        self.deallocate(pointer, old_size, align)?;
        Ok(replacement)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn permanent_static_prefix_survives_allocator_reuse() {
        let initial = vec![0x39; 48];
        let mut heap = Heap::with_statics(&initial, crate::DEFAULT_ALLOCATION_LIMIT);
        assert!(heap.deallocate(TAG + 16, 16, 16).is_err());
        assert!(heap.reallocate(TAG + 16, 16, 16, 32, 256).is_err());
        for _ in 0..3 {
            let a = heap.allocate(17, 64, 256, true).unwrap();
            let b = heap.allocate(8, 8, 256, false).unwrap();
            assert!(a >= TAG + initial.len());
            assert!(b >= TAG + initial.len());
            heap.bytes[a - TAG..a - TAG + 17].fill(0xff);
            heap.deallocate(a, 17, 64).unwrap();
            heap.deallocate(b, 8, 8).unwrap();
            assert_eq!(heap.bytes, initial);
        }
        assert_eq!(heap.allocate(8, 8, initial.len(), false).unwrap(), 0);
        assert_eq!(heap.bytes, initial);
    }

    #[test]
    fn reuse_coalesces_ranges_and_zeroes_old_contents() {
        let mut heap = Heap::default();
        let a = heap.allocate(16, 16, 64, false).unwrap();
        let b = heap.allocate(16, 16, 64, false).unwrap();
        let c = heap.allocate(16, 16, 64, false).unwrap();
        heap.bytes[a - TAG..b - TAG + 16].fill(0xcc);
        heap.bytes[c - TAG..c - TAG + 16].fill(0x39);
        heap.deallocate(a, 16, 16).unwrap();
        heap.deallocate(b, 16, 16).unwrap();
        let reused = heap.allocate(32, 16, 64, true).unwrap();
        assert_eq!(reused, a);
        assert_eq!(&heap.bytes[reused - TAG..reused - TAG + 32], &[0; 32]);
        assert_eq!(&heap.bytes[c - TAG..c - TAG + 16], &[0x39; 16]);
        heap.deallocate(c, 16, 16).unwrap();
        heap.deallocate(reused, 32, 16).unwrap();
        assert!(heap.bytes.is_empty());
    }

    #[test]
    fn reallocation_failure_preserves_original_and_success_preserves_prefix() {
        let mut heap = Heap::default();
        let a = heap.allocate(16, 32, 160, false).unwrap();
        let blocker = heap.allocate(32, 16, 160, false).unwrap();
        for i in 0..16 {
            heap.bytes[a - TAG + i] = i as u8;
        }
        assert_eq!(heap.reallocate(a, 16, 32, 64, 112).unwrap(), 0);
        assert_eq!(heap.allocation(a, 16, 32).unwrap(), a - TAG);
        let moved = heap.reallocate(a, 16, 32, 64, 160).unwrap();
        assert_ne!(moved, a);
        assert_eq!(moved % 32, 0);
        assert_eq!(
            &heap.bytes[moved - TAG..moved - TAG + 16],
            &(0..16).collect::<Vec<u8>>()
        );
        assert_eq!(heap.reallocate(moved, 64, 32, 8, 160).unwrap(), moved);
        assert_eq!(heap.reallocate(moved, 8, 32, 64, 160).unwrap(), moved);
        assert!(heap.deallocate(moved, 8, 32).is_err());
        heap.deallocate(moved, 64, 32).unwrap();
        heap.deallocate(blocker, 32, 16).unwrap();
        assert!(heap.bytes.is_empty());
        assert!(heap.deallocate(blocker, 32, 16).is_err());
    }
}

#[cfg(test)]
mod allocation_budget_tests {
    use super::*;

    #[test]
    fn exact_live_limit_preserves_failure_state_then_allows_zeroed_reuse() {
        let mut h = Heap::with_statics(&[0x39; 16], 2);
        let a = h.allocate(16, 16, 128, false).unwrap();
        let b = h.allocate(16, 16, 128, false).unwrap();
        h.bytes[a - TAG..a - TAG + 16].fill(0xa5);
        let old = h.bytes.clone();
        let allocations = h.allocations.clone();
        let free = h.free.clone();
        assert_eq!(h.allocate(1, 1, 128, false).unwrap(), 0);
        assert_eq!(h.bytes, old);
        assert_eq!(h.allocations, allocations);
        assert_eq!(h.free, free);
        h.deallocate(a, 16, 16).unwrap();
        let c = h.allocate(16, 16, 128, true).unwrap();
        assert_eq!(c, a);
        assert_eq!(&h.bytes[c - TAG..c - TAG + 16], &[0; 16]);
        h.deallocate(b, 16, 16).unwrap();
        h.deallocate(c, 16, 16).unwrap();
        assert_eq!(h.bytes, vec![0x39; 16]);
        let mut zero = Heap::with_statics(&[0x39; 16], 0);
        assert_eq!(zero.allocate(1, 1, 128, false).unwrap(), 0);
        assert_eq!(zero.bytes, vec![0x39; 16]);
    }

    #[test]
    fn realloc_counts_temporary_replacement_and_keeps_original_on_failure() {
        let mut h = Heap::with_statics(&[], 3);
        let a = h.allocate(16, 16, 256, false).unwrap();
        let b = h.allocate(16, 16, 256, false).unwrap();
        let c = h.allocate(16, 16, 256, false).unwrap();
        h.bytes[a - TAG..a - TAG + 16].fill(0xa5);
        // In-place growth/shrink requires no extra count slot.
        assert_eq!(h.reallocate(c, 16, 16, 32, 256).unwrap(), c);
        assert_eq!(h.reallocate(c, 32, 16, 16, 256).unwrap(), c);
        let before = h.bytes.clone();
        assert_eq!(h.reallocate(a, 16, 16, 32, 256).unwrap(), 0);
        assert_eq!(h.bytes, before);
        assert_eq!(h.allocations.len(), 3);
        assert_eq!(h.owned_layout(a - TAG), Some((16, 16)));
        h.deallocate(c, 16, 16).unwrap();
        let moved = h.reallocate(a, 16, 16, 32, 256).unwrap();
        assert_ne!(moved, 0);
        assert_ne!(moved, a);
        assert_eq!(h.allocations.len(), 2);
        assert_eq!(&h.bytes[moved - TAG..moved - TAG + 16], &[0xa5; 16]);
        h.deallocate(b, 16, 16).unwrap();
        h.deallocate(moved, 32, 16).unwrap();
        assert!(h.allocations.is_empty());
        assert!(h.bytes.is_empty());
    }

    #[test]
    fn explicit_count_budget_above_old_default_is_effective() {
        let limit = crate::DEFAULT_ALLOCATION_LIMIT + 1;
        let mut h = Heap::with_statics(&[], limit);
        let pointers: Vec<_> = (0..limit)
            .map(|_| h.allocate(1, 1, limit + 16, false).unwrap())
            .collect();
        assert!(pointers.iter().all(|&p| p != 0));
        assert_eq!(h.allocations.len(), limit);
        assert_eq!(h.allocate(1, 1, limit + 16, false).unwrap(), 0);
        for p in pointers {
            h.deallocate(p, 1, 1).unwrap();
        }
        assert!(h.bytes.is_empty());
        assert!(h.allocations.is_empty());
        assert!(h.free.is_empty());
    }
}
