use super::*;
use crate::{Engine, Limits, Memory, Slot, VERSION, execute_with_engine};

fn memory() -> Memory {
    let mut memory = Memory {
        bytes: (0..256).map(|i| (i * 71) as u8).collect::<Vec<_>>().into(),
        heap: crate::heap::Heap::default(),
        limit: 4096,
        readonly_end: 32,
        peak: 0,
        auxiliary_bytes: 0,
    };
    memory.heap.bytes = (0..192).map(|i| (i * 39 + 117) as u8).collect();
    memory
}

fn leaf(size: usize, write: bool) -> platform::Code {
    let mut a = Assembler {
        heap: true,
        ..Assembler::default()
    };
    a.external_entry();
    a.get(11, 0, false);
    // Only the address sequence changes. Wrap it in the ordinary test ABI:
    // the sequence itself needs no frame cursor, continuation or guest state.
    a.resumable = true;
    a.checked_address(11, size, write);
    a.resumable = false;
    if write {
        a.get(9, 1, false);
        a.get(10, 1, true);
        a.store_mem(9, 10, 11, size);
    } else {
        a.load_mem(9, 10, 11, size);
        a.raw_spill(2, 9, 10);
    }
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

#[test]
fn split_arena_accesses_match_memory_at_all_widths_and_boundaries() {
    for size in 0..=16 {
        for write in [false, true] {
            let code = leaf(size, write);
            let tag = crate::heap::TAG;
            let addresses = [
                0,
                1,
                15,
                16,
                31,
                32,
                33,
                127,
                191,
                192,
                193,
                239,
                240,
                255,
                256,
                257,
                tag - 1,
                tag,
                tag + 1,
                tag + 15,
                tag + 175,
                tag + 176,
                tag + 191,
                tag + 192,
                tag + 193,
                1usize << 63,
                (1usize << 63) + tag,
                usize::MAX,
            ];
            for address in addresses {
                let mut expected = memory();
                let mut actual = memory();
                let value = 0xfeed_cafe_0102_0304_f0e1_d2c3_b4a5_9687u128;
                let result = if write {
                    expected.store(address, size, value).map(|_| None)
                } else {
                    expected.load(address, size).map(Some)
                };
                let mut registers = [address as u128 | (0x1234u128 << 64), value, u128::MAX];
                let before = registers;
                // SAFETY: exclusive initialized backing slices remain stable.
                // Only the emitted checked address can dereference guest input.
                let status = unsafe {
                    code.call(
                        0,
                        registers.as_mut_ptr(),
                        32,
                        actual.bytes.as_mut_ptr(),
                        actual.bytes.len(),
                        actual.readonly_end,
                        actual.heap.bytes.as_mut_ptr(),
                        actual.heap.bytes.len(),
                        std::ptr::null_mut(),
                    )
                };
                assert_eq!(
                    status,
                    if result.is_ok() {
                        0
                    } else {
                        Failure::Memory as u64
                    },
                    "address={address:x} size={size} write={write}"
                );
                let mut wanted = before;
                if let Ok(Some(value)) = result {
                    wanted[2] = value;
                }
                assert_eq!(registers, wanted);
                assert_eq!(actual.bytes.to_vec(), expected.bytes.to_vec());
                assert_eq!(actual.heap.bytes, expected.heap.bytes);
            }
        }
    }
}

#[test]
fn split_arena_copies_validate_both_ranges_before_writing() {
    let tag = crate::heap::TAG;
    let addresses = [
        0,
        1,
        31,
        32,
        127,
        176,
        240,
        255,
        256,
        tag,
        tag + 1,
        tag + 32,
        tag + 176,
        tag + 191,
        tag + 192,
        usize::MAX,
    ];
    for size in [0, 1, 7, 8, 16, 17, 31, 32, 33, 64, 127, 128] {
        let mut a = Assembler {
            heap: true,
            ..Assembler::default()
        };
        a.external_entry();
        a.resumable = true;
        a.lower(&Op::Copy {
            dst: 0,
            src: 1,
            size,
        });
        a.resumable = false;
        a.mov(0, 31);
        a.return_to_vm();
        let failed = a.words.len();
        a.imm(0, Failure::Memory as u64);
        a.return_to_vm();
        for (at, _) in std::mem::take(&mut a.failures) {
            a.patch_conditional(at, failed).unwrap();
        }
        let mut code = platform::Code::reserve(4096).unwrap();
        code.append(&a.words).unwrap();
        for dst in addresses {
            for src in addresses {
                let mut actual = memory();
                let mut expected = memory();
                let success = expected.copy(src, dst, size).is_ok();
                let mut regs = [dst as u128, src as u128];
                let original = regs;
                // SAFETY: both complete ranges are checked by generated code;
                // all host storage is exclusively owned and stable for the call.
                let status = unsafe {
                    code.call(
                        0,
                        regs.as_mut_ptr(),
                        32,
                        actual.bytes.as_mut_ptr(),
                        actual.bytes.len(),
                        actual.readonly_end,
                        actual.heap.bytes.as_mut_ptr(),
                        actual.heap.bytes.len(),
                        std::ptr::null_mut(),
                    )
                };
                assert_eq!(status == 0, success, "src={src:x} dst={dst:x} size={size}");
                assert_eq!(regs, original);
                assert_eq!(actual.bytes.to_vec(), expected.bytes.to_vec());
                assert_eq!(actual.heap.bytes, expected.heap.bytes);
            }
        }
    }
}

#[test]
fn split_arena_regions_preserve_aliases_and_budget_fault_order() {
    for invalid in [false, true] {
        let program = Program {
            version: VERSION,
            target: "aarch64-apple-darwin".into(),
            entry: 0,
            data: vec![0; 16],
            statics: vec![],
            thread_locals: vec![],
            functions: vec![Function {
                name: "arena budget and alias".into(),
                frame_size: 16,
                frame_align: 8,
                registers: 6,
                args: vec![],
                result: Slot { offset: 0, size: 8 },
                code: vec![
                    Op::Imm { dst: 0, value: 8 },
                    Op::Allocate {
                        dst: 1,
                        size: 0,
                        align: 0,
                        zeroed: true,
                    },
                    Op::Imm { dst: 2, value: 37 },
                    Op::Store {
                        address: 1,
                        src: 2,
                        size: 8,
                    },
                    Op::Imm {
                        dst: 3,
                        value: if invalid { 9 } else { 0 },
                    },
                    Op::Binary {
                        dst: 1,
                        overflow: 4,
                        op: Binary::Add,
                        a: 1,
                        b: 3,
                        bits: 64,
                        signed: false,
                    },
                    Op::Load {
                        dst: 1,
                        address: 1,
                        size: 8,
                    },
                    Op::Local { dst: 5, offset: 0 },
                    Op::Store {
                        address: 5,
                        src: 1,
                        size: 8,
                    },
                    Op::Return,
                ],
            }],
        };
        for budget in 0..=12 {
            let expected = execute_with_engine(
                &program,
                &[],
                Limits {
                    instructions: budget,
                    ..Limits::default()
                },
                Engine::Interpreter,
            );
            for persistent in [false, true] {
                for capacity in [0, MAX_CODE_BYTES] {
                    let actual = execute_with_engine(
                        &program,
                        &[],
                        Limits {
                            instructions: budget,
                            jit_resumable_calls: true,
                            jit_persistent_registers: persistent,
                            jit_code_bytes: capacity,
                            ..Limits::default()
                        },
                        Engine::Jit,
                    );
                    match (&expected, actual) {
                        (Ok(expected), Ok(actual)) => {
                            assert_eq!(actual.value, 37);
                            assert_eq!(actual.value, expected.value);
                            assert_eq!(actual.instructions, expected.instructions);
                            assert_eq!(actual.peak_memory, expected.peak_memory);
                        }
                        (Err(expected), Err(actual)) if expected.contains("instruction limit") => {
                            assert_eq!(actual, *expected);
                        }
                        (Err(expected), Err(actual)) => {
                            assert!(expected.contains("memory access"), "{expected}");
                            assert!(actual.contains("memory access"), "{actual}");
                        }
                        (expected, actual) => {
                            panic!("budget={budget} invalid={invalid}: {expected:?} vs {actual:?}")
                        }
                    }
                }
            }
        }
    }
}
