use rust_interp_bytecode::{Function, Limits, Op, Program, Slot, VERSION, execute};

fn fixture(code: Vec<Op>) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![Function {
            name: "entry".into(),
            frame_size: 8,
            frame_align: 16,
            registers: 3,
            args: vec![],
            result: Slot { offset: 0, size: 8 },
            code,
        }],
    }
}

#[test]
fn byte_comparison_checks_complete_ranges_and_unsigned_order() {
    for (left, right, count, expected) in [
        (1, 5, 3, Some(u32::MAX as u128)),
        (5, 1, 3, Some(1)),
        (1, 5, 2, Some(0)),
        (0, 0, 0, Some(0)),
        (1, 5, 24, None),
        (0, 5, 1, None),
        (usize::MAX, 1, 2, None),
    ] {
        let mut p = fixture(vec![
            Op::Imm {
                dst: 0,
                value: left as u128,
            },
            Op::Imm {
                dst: 1,
                value: right as u128,
            },
            Op::Imm {
                dst: 2,
                value: count,
            },
            Op::CompareBytes {
                dst: 0,
                left: 0,
                right: 1,
                size: 2,
            },
            Op::Local { dst: 1, offset: 0 },
            Op::Store {
                address: 1,
                src: 0,
                size: 8,
            },
            Op::Return,
        ]);
        p.data[1..4].copy_from_slice(&[1, 255, 9]);
        p.data[5..8].copy_from_slice(&[1, 255, 10]);
        let got = execute(&p, &[], Limits::default());
        match expected {
            Some(value) => assert_eq!(got.unwrap().value, value),
            None => assert!(got.is_err()),
        }
    }
}

#[test]
fn indirect_calls_validate_handles_and_argument_layouts() {
    use rust_interp_bytecode::{Engine, FUNCTION_POINTER_TAG, execute_with_engine};
    let valid = FUNCTION_POINTER_TAG as u128 | 2;
    for (pointer, arg_size, result_size, passes) in [
        (valid, 8, 8, true),
        (0, 8, 8, false),
        (FUNCTION_POINTER_TAG as u128, 8, 8, false),
        (valid + 90, 8, 8, false),
        (valid | (1 << 100), 8, 8, false),
        (valid, 4, 8, false),
        (valid, 8, 4, false),
    ] {
        let mut p = fixture(vec![
            Op::Imm {
                dst: 0,
                value: pointer,
            },
            Op::Local { dst: 1, offset: 0 },
            Op::Imm { dst: 2, value: 79 },
            Op::Store {
                address: 1,
                src: 2,
                size: 8,
            },
            Op::CallIndirect {
                callee: 0,
                args: vec![1],
                arg_sizes: vec![arg_size],
                destination: 1,
                result_size,
            },
            Op::Return,
        ]);
        p.functions.push(Function {
            name: "callback".into(),
            frame_size: 16,
            frame_align: 16,
            registers: 3,
            args: vec![Slot { offset: 0, size: 8 }],
            result: Slot { offset: 8, size: 8 },
            code: vec![
                Op::Local { dst: 0, offset: 0 },
                Op::Load {
                    dst: 1,
                    address: 0,
                    size: 8,
                },
                Op::Local { dst: 2, offset: 8 },
                Op::Store {
                    address: 2,
                    src: 1,
                    size: 8,
                },
                Op::Return,
            ],
        });
        let mut engines = vec![Engine::Interpreter];
        if cfg!(all(target_arch = "aarch64", target_os = "macos")) {
            engines.push(Engine::Jit);
        }
        for engine in engines {
            let result = execute_with_engine(&p, &[], Limits::default(), engine);
            if passes {
                assert_eq!(result.unwrap().value, 79);
            } else {
                assert!(result.unwrap_err().contains("function"));
            }
        }
    }
}

#[test]
fn public_execution_rejects_malformed_programs() {
    let p = fixture(vec![Op::Imm { dst: 7, value: 0 }, Op::Return]);
    assert!(
        execute(&p, &[], Limits::default())
            .unwrap_err()
            .contains("register")
    );
    let p = fixture(vec![Op::Jump { target: usize::MAX }]);
    assert!(
        execute(&p, &[], Limits::default())
            .unwrap_err()
            .contains("branch")
    );
}

#[test]
fn execution_obeys_instruction_and_memory_budgets() {
    let p = fixture(vec![Op::Jump { target: 0 }]);
    assert!(
        execute(
            &p,
            &[],
            Limits {
                instructions: 17,
                ..Limits::default()
            }
        )
        .unwrap_err()
        .contains("instruction limit")
    );
    let p = fixture(vec![Op::Return]);
    // Guest bytes fit, but the register file would exceed this budget.
    assert!(
        execute(
            &p,
            &[],
            Limits {
                memory: 32,
                ..Limits::default()
            }
        )
        .unwrap_err()
        .contains("memory limit")
    );
    assert!(
        execute(
            &p,
            &[],
            Limits {
                frames: 0,
                ..Limits::default()
            }
        )
        .unwrap_err()
        .contains("call-depth")
    );
}

#[test]
fn guest_memory_cannot_write_constants_or_read_outside_the_machine() {
    let p = fixture(vec![
        Op::Imm { dst: 0, value: 1 },
        Op::Store {
            address: 0,
            src: 0,
            size: 1,
        },
        Op::Return,
    ]);
    assert!(
        execute(&p, &[], Limits::default())
            .unwrap_err()
            .contains("read-only")
    );
    let p = fixture(vec![
        Op::Imm {
            dst: 0,
            value: u64::MAX as u128,
        },
        Op::Load {
            dst: 1,
            address: 0,
            size: 8,
        },
        Op::Return,
    ]);
    assert!(execute(&p, &[], Limits::default()).is_err());
}

#[test]
fn dynamic_copy_uses_guest_addresses_and_fresh_memory() {
    let mut p = fixture(vec![
        Op::Imm { dst: 0, value: 16 },
        Op::Local { dst: 1, offset: 0 },
        Op::Imm { dst: 2, value: 8 },
        Op::CopyDynamic {
            dst: 1,
            src: 0,
            size: 2,
        },
        Op::Return,
    ]);
    p.data.resize(32, 0);
    p.data[16..24].copy_from_slice(&123u64.to_le_bytes());
    assert_eq!(execute(&p, &[], Limits::default()).unwrap().value, 123);
    p.data[16..24].copy_from_slice(&456u64.to_le_bytes());
    assert_eq!(execute(&p, &[], Limits::default()).unwrap().value, 456);
}
