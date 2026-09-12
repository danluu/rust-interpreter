use super::{Memory, heap};

fn memory() -> Memory {
    let mut heap = heap::Heap::default();
    heap.bytes = (0..192).map(|i| (i * 71 + 19) as u8).collect();
    Memory {
        bytes: (0..192).map(|i| (i * 43 + 7) as u8).collect(),
        heap,
        limit: 4096,
        readonly_end: 16,
        peak: 384, auxiliary_bytes: 0,
    }
}

#[test]
fn copies_match_snapshots_for_all_widths_arenas_and_overlaps() {
    for source_heap in [false, true] {
        for destination_heap in [false, true] {
            for size in 0..=65 {
                for source in [32, 33, 47, 64, 81] {
                    for destination in 16..=100 {
                        let mut m = memory();
                        let mut expected_stack = m.bytes.to_vec();
                        let mut expected_heap = m.heap.bytes.clone();
                        let snapshot = if source_heap { &m.heap.bytes[..] } else { &m.bytes[..] }
                            [source..source + size].to_vec();
                        let expected = if destination_heap {
                            &mut expected_heap
                        } else {
                            &mut expected_stack
                        };
                        expected[destination..destination + size].copy_from_slice(&snapshot);
                        let src = source + if source_heap { heap::TAG } else { 0 };
                        let dst = destination + if destination_heap { heap::TAG } else { 0 };
                        m.copy(src, dst, size).unwrap();
                        assert_eq!(&*m.bytes, expected_stack.as_slice(), "stack: {src} {dst} {size}");
                        assert_eq!(m.heap.bytes, expected_heap, "heap: {src} {dst} {size}");
                    }
                }
            }
        }
    }
}

#[test]
fn rejected_copies_leave_both_arenas_unchanged() {
    for size in [1, 2, 3, 4, 8, 15, 16, 17, 64, 65, usize::MAX] {
        for invalid in [0, 192, 193, heap::TAG, heap::TAG + 192, usize::MAX] {
            for (src, dst) in [(invalid, 32), (32, invalid), (invalid, heap::TAG + 32), (heap::TAG + 32, invalid)] {
                let mut m = memory();
                let stack = m.bytes.to_vec();
                let heap = m.heap.bytes.clone();
                assert!(m.copy(src, dst, size).is_err(), "{src} {dst} {size}");
                assert_eq!(&*m.bytes, stack.as_slice());
                assert_eq!(m.heap.bytes, heap);
            }
        }
        for dst in [1, 8, 15] {
            let mut m = memory();
            let stack = m.bytes.to_vec();
            let heap = m.heap.bytes.clone();
            assert!(m.copy(32, dst, size).is_err());
            assert_eq!(&*m.bytes, stack.as_slice());
            assert_eq!(m.heap.bytes, heap);
        }
    }
}

#[test]
fn empty_copies_accept_dangling_addresses_and_constants_remain_readable() {
    let mut m = memory();
    let stack = m.bytes.to_vec();
    let heap = m.heap.bytes.clone();
    for src in [0, 1, 192, heap::TAG, usize::MAX] {
        for dst in [0, 1, 192, heap::TAG, usize::MAX] {
            m.copy(src, dst, 0).unwrap();
            assert_eq!(&*m.bytes, stack.as_slice());
            assert_eq!(m.heap.bytes, heap);
        }
    }
    m.copy(1, 16, 16).unwrap();
    assert_eq!(&m.bytes[16..32], &stack[1..17]);
    // A copy ending exactly at an arena boundary remains valid.
    m.copy(32, heap::TAG + 176, 16).unwrap();
    assert_eq!(&m.heap.bytes[176..192], &m.bytes[32..48]);
}

#[test]
fn scalar_loads_match_little_endian_bytes_at_every_width_and_alignment() {
    let m = memory();
    for is_heap in [false, true] {
        let arena = if is_heap { &m.heap.bytes[..] } else { &m.bytes[..] };
        let tag = if is_heap { heap::TAG } else { 0 };
        for size in 0..=16 {
            // Include every alignment modulo 16 and each exact-end access.
            // Offset 1 also verifies that constant data remains readable.
            for offset in (32..48).chain([1, arena.len() - size]) {
                let expected = arena[offset..offset + size]
                    .iter()
                    .enumerate()
                    .fold(0u128, |value, (index, byte)| {
                        value | (u128::from(*byte) << (8 * index))
                    });
                assert_eq!(
                    m.load(tag + offset, size),
                    Ok(expected),
                    "heap={is_heap}, offset={offset}, size={size}",
                );
            }
        }
    }
}

#[test]
fn scalar_stores_truncate_to_little_endian_bytes_without_touching_neighbors() {
    let values = [
        0,
        1,
        1u128 << 127,
        0x0123_4567_89ab_cdef_fedc_ba98_7654_3210,
        u128::MAX,
    ];
    for is_heap in [false, true] {
        let tag = if is_heap { heap::TAG } else { 0 };
        for size in 0..=16 {
            for offset in (32..48).chain([16, 192 - size]) {
                for value in values {
                    let mut m = memory();
                    let mut expected_stack = m.bytes.to_vec();
                    let mut expected_heap = m.heap.bytes.clone();
                    let expected = if is_heap {
                        &mut expected_heap
                    } else {
                        &mut expected_stack
                    };
                    for index in 0..size {
                        expected[offset + index] = (value >> (8 * index)) as u8;
                    }
                    m.store(tag + offset, size, value).unwrap();
                    assert_eq!(
                        &*m.bytes, expected_stack,
                        "stack: heap={is_heap}, offset={offset}, size={size}, value={value:x}",
                    );
                    assert_eq!(
                        m.heap.bytes, expected_heap,
                        "heap: heap={is_heap}, offset={offset}, size={size}, value={value:x}",
                    );
                }
            }
        }
    }
}

#[test]
fn empty_scalar_accesses_accept_dangling_addresses_without_changing_memory() {
    let mut m = memory();
    let stack = m.bytes.to_vec();
    let heap = m.heap.bytes.clone();
    for address in [0, 1, 15, 192, 193, heap::TAG, heap::TAG + 192, usize::MAX] {
        assert_eq!(m.load(address, 0), Ok(0));
        assert_eq!(m.store(address, 0, u128::MAX), Ok(()));
        assert_eq!(&*m.bytes, stack);
        assert_eq!(m.heap.bytes, heap);
    }
}

#[test]
fn rejected_scalar_accesses_preserve_memory_and_width_error_precedence() {
    let mut m = memory();
    let stack = m.bytes.to_vec();
    let heap = m.heap.bytes.clone();
    for size in 1..=16 {
        for address in [
            0,
            192,
            193,
            193 - size,
            heap::TAG,
            heap::TAG + 192,
            heap::TAG + 193 - size,
            usize::MAX,
        ] {
            assert!(m.load(address, size).is_err(), "load {address} {size}");
            assert!(m.store(address, size, u128::MAX).is_err(), "store {address} {size}");
            assert_eq!(&*m.bytes, stack);
            assert_eq!(m.heap.bytes, heap);
        }
        for address in [1, 8, 15] {
            assert_eq!(
                m.store(address, size, u128::MAX),
                Err("write to read-only guest memory".into()),
            );
            assert_eq!(&*m.bytes, stack);
            assert_eq!(m.heap.bytes, heap);
        }
    }
    for size in (17..=255).chain([usize::MAX]) {
        for address in [0, 1, 32, 192, heap::TAG, heap::TAG + 32, usize::MAX] {
            // Width errors precede both invalid addresses and read-only writes.
            assert_eq!(m.load(address, size), Err("scalar exceeds 128 bits".into()));
            assert_eq!(m.store(address, size, u128::MAX), Err("scalar exceeds 128 bits".into()));
            assert_eq!(&*m.bytes, stack);
            assert_eq!(m.heap.bytes, heap);
        }
    }
}
