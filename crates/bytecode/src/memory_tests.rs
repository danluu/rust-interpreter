use super::{Memory, heap};

fn memory() -> Memory {
    let mut heap = heap::Heap::default();
    heap.bytes = (0..192).map(|i| (i * 71 + 19) as u8).collect();
    Memory {
        bytes: (0..192).map(|i| (i * 43 + 7) as u8).collect(),
        heap,
        limit: 4096,
        readonly_end: 16,
        peak: 384,
        auxiliary_bytes: 0,
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
                        let snapshot = if source_heap {
                            &m.heap.bytes[..]
                        } else {
                            &m.bytes[..]
                        }[source..source + size]
                            .to_vec();
                        let expected = if destination_heap {
                            &mut expected_heap
                        } else {
                            &mut expected_stack
                        };
                        expected[destination..destination + size].copy_from_slice(&snapshot);
                        let src = source + if source_heap { heap::TAG } else { 0 };
                        let dst = destination + if destination_heap { heap::TAG } else { 0 };
                        m.copy(src, dst, size).unwrap();
                        assert_eq!(
                            &*m.bytes,
                            expected_stack.as_slice(),
                            "stack: {src} {dst} {size}"
                        );
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
            for (src, dst) in [
                (invalid, 32),
                (32, invalid),
                (invalid, heap::TAG + 32),
                (heap::TAG + 32, invalid),
            ] {
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
