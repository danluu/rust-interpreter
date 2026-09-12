use rust_interp_bytecode::{
    Engine, Function, HEAP_POINTER_TAG, Limits, Op, Program, Slot, VERSION, execute_with_engine,
    validate,
};

fn program(code: Vec<Op>) -> Program {
    let mut statics = vec![0; 32];
    statics[16..20].copy_from_slice(&7u32.to_le_bytes());
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics,
        thread_locals: vec![Slot {
            offset: 16,
            size: 4,
        }],
        functions: vec![Function {
            name: "C allocation contract".into(),
            frame_size: 64,
            frame_align: 16,
            registers: 8,
            args: vec![],
            result: Slot {
                offset: 0,
                size: 16,
            },
            code,
        }],
    }
}
fn engines() -> Vec<Engine> {
    let mut result = vec![Engine::Interpreter];
    if cfg!(all(target_arch = "aarch64", target_os = "macos")) {
        result.push(Engine::Jit);
    }
    result
}

#[test]
fn allocator_outputs_can_alias_inputs_and_all_budget_tails_agree() {
    for (count, size, expected_errno) in [
        (1, 0, 7),
        (0, u64::MAX as u128, 7),
        (1, 37, 7),
        (u64::MAX as u128, 2, 12),
    ] {
        let p = program(vec![
            Op::Imm {
                dst: 0,
                value: count,
            },
            Op::Imm {
                dst: 1,
                value: size,
            },
            Op::Imm {
                dst: 2,
                value: (HEAP_POINTER_TAG + 16) as u128,
            },
            Op::CAllocate {
                dst: 0,
                count: 0,
                size: 1,
                errno: 2,
                zeroed: true,
            },
            Op::Local { dst: 3, offset: 0 },
            Op::Store {
                address: 3,
                src: 0,
                size: 8,
            },
            Op::CDeallocate { pointer: 0 },
            Op::Load {
                dst: 2,
                address: 2,
                size: 4,
            },
            Op::Local { dst: 3, offset: 8 },
            Op::Store {
                address: 3,
                src: 2,
                size: 8,
            },
            Op::Return,
        ]);
        for engine in engines() {
            for budget in 0..=p.functions[0].code.len() + 1 {
                let result = execute_with_engine(
                    &p,
                    &[],
                    Limits {
                        instructions: budget as u64,
                        ..Limits::default()
                    },
                    engine,
                );
                if budget < p.functions[0].code.len() {
                    assert!(result.unwrap_err().contains("instruction limit"));
                } else {
                    let result = result.unwrap();
                    assert_eq!(result.instructions, p.functions[0].code.len() as u64);
                    assert_eq!(result.value >> 64, expected_errno);
                    let pointer = result.value as u64;
                    if expected_errno == 12 {
                        assert_eq!(pointer, 0);
                    } else {
                        assert!(pointer >= HEAP_POINTER_TAG + 32);
                        assert_eq!(pointer % 16, 0);
                    }
                }
            }
        }
    }
}

#[test]
fn aligned_outputs_preserve_failure_sentinel_and_do_not_clobber_native_inputs() {
    for (align, size, status) in [
        (3, 37, 22),
        (8, 37, 0),
        (64, 0, 0),
        (16, u64::MAX as u128, 12),
    ] {
        let p = program(vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Imm {
                dst: 1,
                value: 0x1234,
            },
            Op::Store {
                address: 0,
                src: 1,
                size: 8,
            },
            Op::Imm {
                dst: 1,
                value: align,
            },
            Op::Imm {
                dst: 2,
                value: size,
            },
            Op::CAlignedAllocate {
                dst: 0,
                output: 0,
                align: 1,
                size: 2,
            },
            Op::Local { dst: 3, offset: 8 },
            Op::Store {
                address: 3,
                src: 0,
                size: 8,
            },
            Op::Return,
        ]);
        for engine in engines() {
            let value = execute_with_engine(&p, &[], Limits::default(), engine)
                .unwrap()
                .value;
            assert_eq!(value >> 64, status);
            if status != 0 {
                assert_eq!(value as u64, 0x1234);
            } else {
                assert_eq!((value as u64 as u128) % align, 0);
                assert_ne!(value as u64, 0);
            }
        }
    }
}

#[test]
fn reallocation_aliases_preserve_failed_input_data() {
    let p = program(vec![
        Op::Imm { dst: 0, value: 1 },
        Op::Imm { dst: 1, value: 16 },
        Op::Imm {
            dst: 2,
            value: (HEAP_POINTER_TAG + 16) as u128,
        },
        Op::CAllocate {
            dst: 0,
            count: 0,
            size: 1,
            errno: 2,
            zeroed: false,
        },
        Op::Imm {
            dst: 3,
            value: 0x71625344,
        },
        Op::Store {
            address: 0,
            src: 3,
            size: 8,
        },
        Op::Imm {
            dst: 1,
            value: u64::MAX as u128,
        },
        Op::CReallocate {
            dst: 1,
            pointer: 0,
            size: 1,
            errno: 2,
        },
        Op::Assert {
            value: 1,
            expected: false,
            message: "failed realloc".into(),
        },
        Op::Load {
            dst: 3,
            address: 0,
            size: 8,
        },
        Op::CDeallocate { pointer: 0 },
        Op::Local { dst: 4, offset: 0 },
        Op::Store {
            address: 4,
            src: 3,
            size: 8,
        },
        Op::Load {
            dst: 2,
            address: 2,
            size: 4,
        },
        Op::Local { dst: 4, offset: 8 },
        Op::Store {
            address: 4,
            src: 2,
            size: 8,
        },
        Op::Return,
    ]);
    for engine in engines() {
        assert_eq!(
            execute_with_engine(&p, &[], Limits::default(), engine)
                .unwrap()
                .value,
            (12u128 << 64) | 0x71625344
        );
    }
}

#[test]
fn c_opcodes_validate_registers_target_and_wide_pointers() {
    let ops = [
        Op::CAllocate {
            dst: 8,
            count: 0,
            size: 0,
            errno: 0,
            zeroed: false,
        },
        Op::CDeallocate { pointer: 8 },
        Op::CReallocate {
            dst: 0,
            pointer: 0,
            size: 0,
            errno: 8,
        },
        Op::CAlignedAllocate {
            dst: 0,
            output: 8,
            align: 0,
            size: 0,
        },
    ];
    for op in ops {
        assert!(validate(&program(vec![op, Op::Return])).is_err());
    }
    let mut p = program(vec![Op::CDeallocate { pointer: 0 }, Op::Return]);
    p.target = "x86_64-unknown-linux-gnu".into();
    assert!(validate(&p).unwrap_err().contains("Darwin"));
    let p = program(vec![
        Op::Imm {
            dst: 0,
            value: 1u128 << 64,
        },
        Op::CDeallocate { pointer: 0 },
        Op::Return,
    ]);
    for engine in engines() {
        assert!(
            execute_with_engine(&p, &[], Limits::default(), engine)
                .unwrap_err()
                .contains("pointer width")
        );
    }
}
