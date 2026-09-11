use super::*;
use crate::{Engine, Limits, Memory, Slot, VERSION, execute_profiled, execute_with_engine};

fn memory(heap: bool) -> Memory {
    let mut m = Memory {
        bytes: (0..4096)
            .map(|i| (i * 71 + i / 256) as u8)
            .collect::<Vec<_>>()
            .into(),
        heap: crate::heap::Heap::default(),
        limit: 16384,
        readonly_end: 128,
        peak: 0,
        auxiliary_bytes: 0,
    };
    if heap {
        m.heap.bytes = (0..4096).map(|i| (i * 39 + 117) as u8).collect();
    }
    m
}

fn leaf(heap: bool, op: Op) -> platform::Code {
    // The production transfer has no dependency on resumable metadata. Test
    // its bytes with an ordinary ABI wrapper, independent of VM frame setup.
    let mut a = Assembler {
        heap,
        ..Assembler::default()
    };
    a.external_entry();
    a.copy_transfer(&op).unwrap();
    a.mov(0, 31);
    a.return_to_vm();
    let failed = a.words.len();
    a.imm(0, Failure::Memory as u64);
    a.return_to_vm();
    for (at, kind) in std::mem::take(&mut a.failures) {
        assert!(kind == Failure::Memory);
        a.patch_conditional(at, failed).unwrap();
    }
    let mut code = platform::Code::reserve(4096).unwrap();
    code.append(&a.words).unwrap();
    code
}

fn probe(code: &platform::Code, heap: bool, dst: u128, src: u128, count: u128, size: usize) {
    let mut actual = memory(heap);
    let mut expected = memory(heap);
    let success = expected.copy(src as usize, dst as usize, size).is_ok();
    let mut registers = [dst, src, count, u128::MAX, 0x1234, 0, 0xabcd];
    let before = registers;
    // SAFETY: the leaf owns all emitted guards; both backing slices are live,
    // exclusive and stable. Invalid guest ranges are tested only through those
    // guards. No raw host address comes from a guest argument.
    let result = unsafe {
        code.call(
            0,
            registers.as_mut_ptr(),
            128,
            actual.bytes.as_mut_ptr(),
            actual.bytes.len(),
            actual.readonly_end,
            actual.heap.bytes.as_mut_ptr(),
            actual.heap.bytes.len(),
            std::ptr::null_mut(),
        )
    };
    assert_eq!(
        result,
        if success { 0 } else { Failure::Memory as u64 },
        "dst={dst:x} src={src:x} count={count:x} size={size}"
    );
    assert_eq!(registers, before);
    assert_eq!(
        actual.bytes.to_vec(),
        expected.bytes.to_vec(),
        "stack dst={dst:x} src={src:x} size={size}"
    );
    assert_eq!(
        actual.heap.bytes, expected.heap.bytes,
        "heap dst={dst:x} src={src:x} size={size}"
    );
}

#[test]
fn native_transfers_match_memmove_for_overlaps_alignments_lengths_and_arenas() {
    let code = leaf(
        true,
        Op::CopyDynamic {
            dst: 0,
            src: 1,
            size: 2,
        },
    );
    let lengths: Vec<usize> = (0..=33)
        .chain([
            63, 64, 65, 127, 128, 129, 136, 255, 256, 257, 336, 352, 511, 512, 513, 1023, 1024,
            1025,
        ])
        .collect();
    for &size in &lengths {
        for align in 0..16 {
            for shift in [
                -129isize, -33, -32, -31, -17, -16, -15, -8, -2, -1, 0, 1, 2, 8, 15, 16, 17, 31,
                32, 33, 129,
            ] {
                for source_arena in [0, crate::heap::TAG] {
                    for destination_arena in [0, crate::heap::TAG] {
                        let src = 512 + align + source_arena;
                        let dst = (512isize + align as isize + shift) as usize + destination_arena;
                        probe(&code, true, dst as u128, src as u128, size as u128, size);
                    }
                }
            }
        }
    }
}

#[test]
fn native_transfers_check_both_full_ranges_before_writing_and_accept_empty_ranges() {
    for heap in [false, true] {
        let code = leaf(
            heap,
            Op::CopyDynamic {
                dst: 0,
                src: 1,
                size: 2,
            },
        );
        for size in [0, 1, 15, 16, 17, 129, 512, 4096, usize::MAX] {
            let mut addresses = vec![
                0,
                1,
                127,
                128,
                4095,
                4096,
                4097,
                usize::MAX,
                crate::heap::TAG,
                crate::heap::TAG + 1,
                crate::heap::TAG + 4095,
                crate::heap::TAG + 4096,
            ];
            if size <= 4096 {
                addresses.extend([4096 - size, 4097 - size]);
            }
            for address in addresses {
                for (dst, src) in [(address, 512), (512, address), (address, address)] {
                    probe(&code, heap, dst as u128, src as u128, size as u128, size);
                }
            }
        }
        // Preserve the existing bytecode's low-usize conversion for all inputs.
        probe(
            &code,
            heap,
            (1u128 << 100) | 513,
            (1u128 << 90) | 512,
            (1u128 << 80) | 129,
            129,
        );
    }
}

#[test]
fn native_fixed_transfers_share_checked_overlap_semantics_and_preserve_host_abi() {
    for size in [129, 136, 255, 256, 257, 336, 352, 1024, 4097, usize::MAX] {
        let code = leaf(
            true,
            Op::Copy {
                dst: 0,
                src: 1,
                size,
            },
        );
        for shift in [-17isize, -1, 0, 1, 17] {
            probe(&code, true, (512isize + shift) as u128, 512, 0, size);
        }
        let mut m = memory(true);
        let mut registers = [513u128, 512, 0];
        let arguments = [
            registers.as_mut_ptr() as usize,
            128,
            m.bytes.as_mut_ptr() as usize,
            m.bytes.len(),
            m.readonly_end,
            m.heap.bytes.as_mut_ptr() as usize,
            m.heap.bytes.len(),
            0,
        ];
        // SAFETY: same guarded, exclusively owned leaf contract as probe.
        let out = unsafe { code.tree_abi_probe(0, arguments) };
        assert_eq!(
            [out[1], out[2], out[3], out[4]],
            [0x1357, 0x2468, 0x3579, 0x468a]
        );
        assert_eq!(out[5], out[6]); // frame pointer and stack pointer
        assert_eq!(&out[7..], &[0x579b, 0x68ac, 0x79bd, 0x8ace, 0x9bdf, 0xace0]);
    }
}

fn program(size: usize, dynamic: bool) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: (0..2048).map(|i| (i * 71 + 11) as u8).collect(),
        statics: vec![],
        thread_locals: vec![],
        functions: vec![Function {
            name: "copy continuation".into(),
            frame_size: 2048,
            frame_align: 16,
            registers: 8,
            args: vec![],
            result: Slot {
                offset: 0,
                size: 16,
            },
            code: vec![
                Op::Local {
                    dst: 0,
                    offset: 128,
                },
                Op::Imm { dst: 1, value: 257 },
                Op::Imm {
                    dst: 2,
                    value: size as u128,
                },
                Op::Imm {
                    dst: 3,
                    value: u128::MAX,
                },
                Op::Jump { target: 5 },
                Op::Store {
                    address: 0,
                    src: 3,
                    size: 16,
                },
                Op::Load {
                    dst: 4,
                    address: 0,
                    size: 8,
                },
                if dynamic {
                    Op::CopyDynamic {
                        dst: 0,
                        src: 1,
                        size: 2,
                    }
                } else {
                    Op::Copy {
                        dst: 0,
                        src: 1,
                        size,
                    }
                },
                Op::Load {
                    dst: 5,
                    address: 0,
                    size: 8,
                },
                Op::Local { dst: 6, offset: 0 },
                Op::Store {
                    address: 6,
                    src: 5,
                    size: 16,
                },
                // An interpreted operation forces a continuation after the
                // copy, observing a cached full-width value across it.
                Op::Unary {
                    dst: 7,
                    src: 3,
                    bits: 128,
                    op: Unary::CountOnes,
                },
                Op::Imm { dst: 2, value: 128 },
                Op::Binary {
                    dst: 1,
                    overflow: 0,
                    op: Binary::Eq,
                    a: 7,
                    b: 2,
                    bits: 64,
                    signed: false,
                },
                Op::Assert {
                    value: 1,
                    expected: true,
                    message: "copy clobbered cached value".into(),
                },
                Op::Return,
            ],
        }],
    }
}

#[test]
fn resumable_transfers_preserve_budgets_profiles_local_facts_and_code_limit_decline() {
    for dynamic in [false, true] {
        for size in [0, 1, 15, 16, 17, 129, 136, 352, 1025] {
            let p = program(size, dynamic);
            for persistent in [false, true] {
                for code_bytes in [0, MAX_CODE_BYTES] {
                    for budget in 0..=17 {
                        let limits = || Limits {
                            instructions: budget,
                            jit_code_bytes: code_bytes,
                            jit_resumable_calls: true,
                            jit_persistent_registers: persistent,
                            ..Limits::default()
                        };
                        let ordinary = || Limits {
                            instructions: budget,
                            ..Limits::default()
                        };
                        let interpreted =
                            execute_with_engine(&p, &[], ordinary(), Engine::Interpreter);
                        let jit = execute_with_engine(&p, &[], limits(), Engine::Jit);
                        let observed = execute_profiled(&p, &[], limits(), Engine::Jit);
                        if budget < 16 {
                            assert_eq!(
                                interpreted.unwrap_err(),
                                "interpreter instruction limit exceeded"
                            );
                            assert_eq!(jit.unwrap_err(), "interpreter instruction limit exceeded");
                            assert_eq!(
                                observed.unwrap_err(),
                                "interpreter instruction limit exceeded"
                            );
                        } else {
                            let expected = interpreted.unwrap();
                            let actual = jit.unwrap();
                            let (sampled, profile) = observed.unwrap();
                            assert_eq!(actual.value, expected.value);
                            assert_eq!(sampled.value, expected.value);
                            assert_eq!(actual.instructions, expected.instructions);
                            assert_eq!(sampled.instructions, expected.instructions);
                            assert_eq!(actual.peak_memory, expected.peak_memory);
                            assert_eq!(
                                profile.functions[0].interpreted[7],
                                u64::from(code_bytes == 0)
                            );
                            if persistent && code_bytes > 0 {
                                assert!(actual.jit_register_pairs > 0);
                            }
                        }
                    }
                }
            }
        }
    }
}
