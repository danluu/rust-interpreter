//! Darwin C allocation in guest arenas. No guest address reaches host libc.
use crate::{heap, Memory};

const ENOMEM: u128 = 12;
const EINVAL: u128 = 22;
const MALLOC_ALIGN: usize = 16;

fn word(value: u128) -> Result<usize, String> {
    usize::try_from(value).map_err(|_| "C allocator operand exceeds the guest pointer width".into())
}

impl heap::Heap {
    fn c_layout(&self, pointer: usize) -> Result<(usize, usize), String> {
        let offset = pointer.checked_sub(heap::TAG).ok_or("invalid C allocation pointer")?;
        self.owned_layout(offset).ok_or_else(|| "C pointer does not name an owned allocation".into())
    }

    fn c_allocate(&mut self, size: usize, align: usize, budget: usize, zeroed: bool) -> Result<usize, String> {
        // These are valid C requests that cannot fit in the guest address space.
        // The Rust layout API remains unchanged, including its nonzero-size rule.
        if align > heap::TAG || size >= heap::TAG { return Ok(0); }
        self.allocate(size.max(1), align, budget, zeroed)
    }

    fn c_deallocate(&mut self, pointer: usize) -> Result<(), String> {
        if pointer == 0 { return Ok(()); }
        let (size, align) = self.c_layout(pointer)?;
        self.deallocate(pointer, size, align)
    }

    fn c_reallocate(&mut self, pointer: usize, size: usize, budget: usize) -> Result<usize, String> {
        if pointer == 0 { return self.c_allocate(size, MALLOC_ALIGN, budget, false); }
        let (old_size, align) = self.c_layout(pointer)?;
        if size == 0 {
            // Darwin allocates the new minimum object before releasing the old.
            let replacement = self.c_allocate(0, MALLOC_ALIGN, budget, false)?;
            if replacement != 0 { self.deallocate(pointer, old_size, align)?; }
            return Ok(replacement);
        }
        if size >= heap::TAG { return Ok(0); }
        self.reallocate(pointer, old_size, align, size, budget)
    }
}

impl Memory {
    fn c_output(&self, address: u128, size: usize) -> Result<usize, String> {
        let address = word(address)?;
        let (is_heap, _) = self.range(address, size)?;
        if !is_heap && address < self.readonly_end {
            return Err("write to read-only guest memory".into());
        }
        Ok(address)
    }

    pub(super) fn c_allocate(&mut self, count: u128, size: u128, errno: u128,
        zeroed: bool, registers: usize) -> Result<u128, String> {
        let count = word(count)?;
        let size = word(size)?;
        let errno = self.c_output(errno, 4)?;
        let pointer = match count.checked_mul(size) {
            Some(size) => self.heap.c_allocate(size, MALLOC_ALIGN, self.heap_budget(registers), zeroed)?,
            None => 0,
        };
        if pointer == 0 { self.store(errno, 4, ENOMEM)?; }
        self.peak = self.peak.max(self.total_len());
        Ok(pointer as u128)
    }

    pub(super) fn c_deallocate(&mut self, pointer: u128) -> Result<(), String> {
        self.heap.c_deallocate(word(pointer)?)
    }

    pub(super) fn c_reallocate(&mut self, pointer: u128, size: u128, errno: u128,
        registers: usize) -> Result<u128, String> {
        let pointer = word(pointer)?;
        let size = word(size)?;
        let errno = self.c_output(errno, 4)?;
        let replacement = self.heap.c_reallocate(pointer, size, self.heap_budget(registers))?;
        if replacement == 0 { self.store(errno, 4, ENOMEM)?; }
        self.peak = self.peak.max(self.total_len());
        Ok(replacement as u128)
    }

    pub(super) fn c_aligned_allocate(&mut self, output: u128, align: u128, size: u128,
        registers: usize) -> Result<u128, String> {
        let output = word(output)?;
        let align = word(align)?;
        let size = word(size)?;
        if align < 8 || !align.is_power_of_two() { return Ok(EINVAL); }
        let output = self.c_output(output as u128, 8)?;
        let pointer = self.heap.c_allocate(size, align, self.heap_budget(registers), false)?;
        if pointer == 0 { return Ok(ENOMEM); }
        self.store(output, 8, pointer as u128)?;
        self.peak = self.peak.max(self.total_len());
        Ok(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn memory(limit: usize) -> Memory {
        Memory { bytes: vec![0; 64], heap: heap::Heap::with_statics(&[0; 32], crate::DEFAULT_ALLOCATION_LIMIT),
            readonly_end: 16, limit, peak: 96, auxiliary_bytes: 0 }
    }

    #[test]
    fn zero_sizes_overflow_alignment_and_errno_match_native_contracts() {
        let mut m = memory(16_384);
        for (count, size) in [(1, 0), (0, usize::MAX as u128), (37, 1)] {
            m.store(16, 4, 7).unwrap();
            let p = m.c_allocate(count, size, 16, true, 0).unwrap();
            assert!(p >= (heap::TAG + 32) as u128);
            assert_eq!(p % 16, 0);
            assert_eq!(m.load(16, 4).unwrap(), 7);
            if count * size != 0 { assert!(m.read(p as usize, 37).unwrap().iter().all(|&b| b == 0)); }
            m.c_deallocate(p).unwrap();
        }
        for (count, size) in [(1, usize::MAX as u128), (usize::MAX as u128, 2)] {
            assert_eq!(m.c_allocate(count, size, 16, false, 0).unwrap(), 0);
            assert_eq!(m.load(16, 4).unwrap(), ENOMEM);
        }
        for align in [0, 3, 4, 12, 8, 16, 64, 4096, 1u128 << 63] {
            m.store(24, 8, 0x1234).unwrap();
            m.store(16, 4, 7).unwrap();
            let status = m.c_aligned_allocate(24, align, 37, 0).unwrap();
            if align < 8 || !align.is_power_of_two() {
                assert_eq!(status, EINVAL);
                assert_eq!(m.load(24, 8).unwrap(), 0x1234);
            } else if align > heap::TAG as u128 {
                assert_eq!(status, ENOMEM);
                assert_eq!(m.load(24, 8).unwrap(), 0x1234);
            } else {
                assert_eq!(status, 0);
                let p = m.load(24, 8).unwrap();
                assert_ne!(p, 0);
                assert_eq!(p % align, 0);
                m.c_deallocate(p).unwrap();
            }
            assert_eq!(m.load(16, 4).unwrap(), 7);
        }
        assert_eq!(m.c_aligned_allocate(24, 64, 0, 0).unwrap(), 0);
        let p = m.load(24, 8).unwrap();
        assert_eq!(p % 64, 0);
        m.c_deallocate(p).unwrap();
        m.c_deallocate(0).unwrap();
        assert_eq!(m.load(16, 4).unwrap(), 7);
        assert_eq!(m.heap.bytes.len(), 32);
    }

    #[test]
    fn realloc_preserves_failed_allocation_and_replaces_zero_sized_object() {
        let mut m = memory(1024);
        let p = m.c_allocate(1, 37, 16, false, 0).unwrap();
        for i in 0..37 { m.store(p as usize + i, 1, (i + 11) as u128).unwrap(); }
        assert_eq!(m.c_reallocate(p, usize::MAX as u128, 16, 0).unwrap(), 0);
        assert_eq!(m.load(16, 4).unwrap(), ENOMEM);
        for i in 0..37 { assert_eq!(m.load(p as usize + i, 1).unwrap(), (i + 11) as u128); }
        let grown = m.c_reallocate(p, 113, 16, 0).unwrap();
        for i in 0..37 { assert_eq!(m.load(grown as usize + i, 1).unwrap(), (i + 11) as u128); }
        let zero = m.c_reallocate(grown, 0, 16, 0).unwrap();
        assert_ne!(zero, 0);
        assert_ne!(zero, grown);
        assert!(m.c_deallocate(grown).is_err());
        m.c_deallocate(zero).unwrap();
        let from_null = m.c_reallocate(0, 0, 16, 0).unwrap();
        assert_ne!(from_null, 0);
        m.c_deallocate(from_null).unwrap();

        // Exactly enough room for the existing allocation, but not its zero-size
        // replacement. Failure must not release the old object.
        let p = m.c_allocate(1, 37, 16, false, 0).unwrap();
        m.limit = m.total_len();
        assert_eq!(m.c_reallocate(p, 0, 16, 0).unwrap(), 0);
        assert_eq!(m.heap.c_layout(p as usize).unwrap().0, 37);
        m.c_deallocate(p).unwrap();
    }

    #[test]
    fn pointer_validation_and_working_memory_budget_precede_mutation() {
        let mut m = memory(128);
        let p = m.c_allocate(1, 16, 16, true, 16).unwrap();
        assert_ne!(p, 0);
        let old_heap = m.heap.bytes.clone();
        for invalid in [1, (heap::TAG + 16) as u128, p + 1, p | (1u128 << 64)] {
            assert!(m.c_deallocate(invalid).is_err());
            assert!(m.c_reallocate(invalid, 8, 16, 0).is_err());
            assert_eq!(m.heap.bytes, old_heap);
        }
        assert_eq!(m.c_allocate(1, 1, 16, true, 16).unwrap(), 0);
        assert_eq!(m.load(16, 4).unwrap(), ENOMEM);
        assert!(m.c_allocate(1u128 << 64, 1, 16, false, 0).is_err());
        for invalid in [0, 8, 63, 16 | (1u128 << 64)] {
            assert!(m.c_allocate(1, 1, invalid, false, 0).is_err());
            assert!(m.c_aligned_allocate(invalid, 16, 1, 0).is_err());
            assert_eq!(m.heap.bytes, old_heap);
        }
        m.c_deallocate(p).unwrap();
        assert!(m.c_deallocate(p).is_err());
        assert_eq!(m.heap.bytes, vec![0; 32]);
    }
}

#[cfg(test)]
mod allocation_budget_boundary_tests {
    use super::*;
    fn memory(allocations:usize)->Memory {
        Memory {bytes:vec![0;64],heap:heap::Heap::with_statics(&[0x39;32],allocations),
            readonly_end:16,limit:4096,peak:96,auxiliary_bytes:0}
    }
    #[test]
    fn rust_and_c_families_share_one_count_budget() {
        let mut m=memory(2);
        let rust=m.heap.allocate(16,16,2048,false).unwrap();
        m.heap.bytes[rust-heap::TAG..rust-heap::TAG+16].fill(0xa5);
        let c=m.c_allocate(1,16,16,true,0).unwrap();assert_ne!(c,0);
        assert_eq!(m.c_allocate(1,1,16,false,0).unwrap(),0);
        assert_eq!(m.load(16,4).unwrap(),ENOMEM);
        m.store(24,8,0x1234).unwrap();
        assert_eq!(m.c_aligned_allocate(24,64,1,0).unwrap(),ENOMEM);
        assert_eq!(m.load(24,8).unwrap(),0x1234);
        // In-place growth is legal while moving growth requires a spare slot.
        assert_eq!(m.c_reallocate(c,32,16,0).unwrap(),c);
        assert_eq!(m.heap.reallocate(rust,16,16,32,2048).unwrap(),0);
        assert_eq!(m.read(rust,16).unwrap(),&[0xa5;16]);
        m.c_deallocate(c).unwrap();
        let resized=m.heap.reallocate(rust,16,16,32,2048).unwrap();assert_eq!(resized,rust);
        assert_eq!(m.read(rust,16).unwrap(),&[0xa5;16]);
        m.heap.deallocate(resized,32,16).unwrap();
        assert_eq!(m.heap.bytes,vec![0x39;32]);
        let reused=m.heap.allocate(1,1,2048,false).unwrap();assert_ne!(reused,0);
        m.heap.deallocate(reused,1,1).unwrap();
    }
    #[test]
    fn zero_count_budget_preserves_c_error_outputs_and_validation_order() {
        let mut m=memory(0);
        for size in [0,1,16] {
            m.store(16,4,7).unwrap();m.store(24,8,0x1234).unwrap();
            assert_eq!(m.c_allocate(1,size,16,true,0).unwrap(),0);
            assert_eq!(m.load(16,4).unwrap(),ENOMEM);
            assert_eq!(m.c_reallocate(0,size,16,0).unwrap(),0);
            assert_eq!(m.c_aligned_allocate(24,64,size,0).unwrap(),ENOMEM);
            assert_eq!(m.load(24,8).unwrap(),0x1234);
        }
        assert_eq!(m.c_aligned_allocate(24,3,16,0).unwrap(),EINVAL);
        assert_eq!(m.c_allocate(1,16,0,false,0).unwrap_err(),"invalid guest memory access");
        assert_eq!(m.c_aligned_allocate(0,64,16,0).unwrap_err(),"invalid guest memory access");
        assert_eq!(m.c_allocate(1,16,8,false,0).unwrap_err(),"write to read-only guest memory");
        assert_eq!(m.c_aligned_allocate(8,64,16,0).unwrap_err(),"write to read-only guest memory");
        assert_eq!(m.heap.bytes,vec![0x39;32]);
    }
    #[test]
    fn zero_sized_c_realloc_counts_the_temporary_replacement() {
        for count_limit in [1,2] {
            let mut m=memory(count_limit);
            let p=m.c_allocate(1,16,16,false,0).unwrap();m.store(p as usize,1,0xa5).unwrap();
            let q=m.c_reallocate(p,0,16,0).unwrap();
            if count_limit==1 {
                assert_eq!(q,0);assert_eq!(m.load(p as usize,1).unwrap(),0xa5);
                assert_eq!(m.load(16,4).unwrap(),ENOMEM);m.c_deallocate(p).unwrap();
            } else {
                assert_ne!(q,0);assert_ne!(q,p);assert!(m.c_deallocate(p).is_err());m.c_deallocate(q).unwrap();
            }
            assert_eq!(m.heap.bytes,vec![0x39;32]);
        }
    }
}
