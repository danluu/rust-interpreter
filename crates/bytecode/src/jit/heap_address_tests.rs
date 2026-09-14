use super::*;

// Independent of the emitter's subtraction/selection sequence: classify the
// start, then compare a wide mathematical end with the chosen backing length.
fn oracle(raw: u64, count: u64, write: bool, heap: bool, linear: u64,
    arena: u64, readonly: u64, linear_host: u64, heap_host: u64) -> u64 {
    if count == 0 { return linear_host; }
    let in_heap = heap && raw >= crate::heap::TAG as u64;
    let offset = raw as u128 - if in_heap { crate::heap::TAG as u128 } else { 0 };
    let length = if in_heap { arena } else { linear };
    if offset == 0 || offset + count as u128 > length as u128
        || (write && !in_heap && offset < readonly as u128) {
        return Failure::Memory as u64;
    }
    (if in_heap { heap_host } else { linear_host }).wrapping_add(offset as u64)
}

fn leaf(heap: bool, write: bool, fixed: Option<u64>, address: u32) -> Vec<u32> {
    let mut a = Assembler { heap, ..Assembler::default() };
    // Only this diagnostic leaf replaces extents with synthetic numbers. It
    // never dereferences the computed address or accesses either byte arena.
    for (slot, reg) in [(0,3), (1,6), (2,4), (3,10)] {
        a.emit(0xf9400000 | (slot * 2 << 10) | reg);
    }
    if heap { a.initialize_heap_context(); }
    a.imm(5, 0x1357); a.imm(6, 0x2468);
    for reg in [9,11,12,16] { a.imm(reg, 0x1000 + reg as u64); }
    a.mov(address, 1);
    match fixed {
        Some(size) => a.checked_address(address, size as usize, write),
        None => a.dynamic_address(address, 10, write),
    }
    let done = a.words.len(); a.emit(0x14000000);
    let failure = a.words.len(); a.imm(address, Failure::Memory as u64);
    let publish = a.words.len();
    a.words[done] |= (publish - done) as u32;
    for (slot, reg) in [(4,5),(5,6),(6,10),(7,9),(8,11),(9,12),(10,16)] {
        a.emit(0xf9000000 | (slot * 2 << 10) | reg);
    }
    a.mov(0, address); a.emit(0xd65f03c0);
    for (at, kind) in std::mem::take(&mut a.failures) {
        assert!(matches!(kind, Failure::Memory));
        a.patch_conditional(at, failure).unwrap();
    }
    a.words
}

fn cases(code: &mut platform::Code, heap: bool, write: bool, fixed: Option<u64>,
    address: u32, extents: &[(u64,u64,u64)], counts: &[u64]) {
    let entry = code.append(&leaf(heap, write, fixed, address)).unwrap();
    let tag = crate::heap::TAG as u64;
    let mut linear = [0xa5u8; 256]; let mut arena = [0x5au8; 192];
    for &(len, heap_len, readonly) in extents {
        assert!(len <= isize::MAX as u64 && heap_len <= isize::MAX as u64 && readonly <= len);
        let mut addresses = vec![0,1,7,8,15,16,31,32,127,128,191,192,255,256,
            tag-1,tag,tag+1,tag+191,tag+192,2*tag-1,2*tag,2*tag+1,
            3*tag-1,3*tag,u64::MAX-7,u64::MAX];
        for boundary in [len,readonly,tag+heap_len] {
            addresses.extend([boundary.saturating_sub(1),boundary,boundary.saturating_add(1)]);
        }
        for raw in addresses { for &count in counts {
            if let Some(size) = fixed { assert_eq!(count,size); }
            else { assert_ne!(count,0); } // dynamic callers bypass empty ranges
            let mut regs = [0xfeed_cafe_0000_0000_0000_0000_0000_0000u128; 12];
            for (i,v) in [len,heap_len,readonly,count].into_iter().enumerate() { regs[i] |= v as u128; }
            let before = regs;
            // SAFETY: this owned leaf only reads/writes the bounded register
            // array. Synthetic extents are data for checks, never permission to
            // dereference a pointee. Actual passed arenas are live and stable.
            let got = unsafe { code.call(entry,regs.as_mut_ptr(),raw as usize,
                linear.as_mut_ptr(),linear.len(),0,arena.as_mut_ptr(),arena.len(),std::ptr::null_mut()) };
            let expected = oracle(raw,count,write,heap,len,heap_len,readonly,
                linear.as_ptr() as u64,arena.as_ptr() as u64);
            assert_eq!(got,expected,"heap={heap} write={write} fixed={fixed:?} rd={address} raw={raw:x} count={count} extents={len}/{heap_len}/{readonly}");
            assert_eq!(&regs[..4],&before[..4]);
            assert_eq!((regs[4] as u64,regs[5] as u64,regs[6] as u64),(0x1357,0x2468,count));
            for (slot,reg) in [(7,9),(8,11),(9,12),(10,16)] {
                if reg != address { assert_eq!(regs[slot] as u64,0x1000+reg as u64); }
            }
            for i in 4..12 { assert_eq!(regs[i] >> 64,before[i] >> 64); }
        }}
    }
    assert_eq!(linear,[0xa5;256]); assert_eq!(arena,[0x5a;192]);
}

#[test]
fn fixed_checks_match_wide_oracle_and_preserve_cached_values() {
    let mut code = platform::Code::reserve(2*1024*1024).unwrap();
    let tag = crate::heap::TAG as u64;
    let extents = [(0,0,0),(256,192,32),(256,0,256),(0,192,0),
        (tag+8,tag-1,tag-1),(isize::MAX as u64,isize::MAX as u64,tag)];
    for heap in [false,true] { for write in [false,true] { for address in [9,11,12] {
        for size in [0,1,2,3,4,7,8,9,16,31,32,128,4096,tag,u64::MAX] {
            cases(&mut code,heap,write,Some(size),address,&extents,&[size]);
        }
    }}}
}

#[test]
fn dynamic_checks_match_wide_oracle_at_both_tag_bits_and_full_counts() {
    let mut code = platform::Code::reserve(1024*1024).unwrap();
    let tag = crate::heap::TAG as u64;
    let extents = [(0,0,0),(256,192,32),(256,0,256),(0,192,0),
        (tag+8,tag-1,tag-1),(isize::MAX as u64,isize::MAX as u64,tag)];
    for heap in [false,true] { for write in [false,true] { for address in [9,11,12] {
        cases(&mut code,heap,write,None,address,&extents,
            &[1,2,3,8,16,32,128,4096,tag,2*tag,u64::MAX]);
    }}}
}
