use rust_interp_bytecode::{
    Engine, Function, Limits, Op, Program, Slot, VERSION, execute_with_engine,
};

fn program(code: Vec<Op>, frame_size: usize, result_size: usize) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![], thread_locals: vec![],
        functions: vec![Function {
            name: "entry".into(),
            registers: 8,
            frame_size,
            frame_align: 16,
            args: vec![],
            result: Slot {
                offset: 0,
                size: result_size,
            },
            code,
        }],
    }
}

fn check(p: &Program, expected: u128) {
    let mut engines = vec![Engine::Interpreter];
    if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
        engines.push(Engine::Jit);
    }
    for engine in engines {
        let got = execute_with_engine(p, &[], Limits::default(), engine).unwrap();
        assert_eq!(got.value, expected);
        if engine == Engine::Jit {
            assert!(got.jit_instructions > 0);
        }
    }
}

#[test]
fn jit_heap_scalar_widths_and_cross_arena_copies() {
    let value = 0xfedcba98765432100123456789abcdefu128;
    for width in 0..=16 {
        let p = program(
            vec![
                Op::Imm { dst: 0, value: 32 },
                Op::Imm { dst: 1, value: 64 },
                Op::Allocate {
                    dst: 2,
                    size: 0,
                    align: 1,
                    zeroed: true,
                },
                Op::Imm { dst: 3, value },
                Op::Store {
                    address: 2,
                    src: 3,
                    size: 16,
                },
                Op::Local { dst: 4, offset: 16 },
                Op::Copy {
                    dst: 4,
                    src: 2,
                    size: 32,
                },
                Op::Copy {
                    dst: 2,
                    src: 4,
                    size: 32,
                },
                Op::Load {
                    dst: 3,
                    address: 2,
                    size: width,
                },
                Op::Local { dst: 4, offset: 0 },
                Op::Store {
                    address: 4,
                    src: 3,
                    size: 16,
                },
                Op::Deallocate {
                    pointer: 2,
                    size: 0,
                    align: 1,
                },
                Op::Return,
            ],
            48,
            16,
        );
        let mask = if width == 16 {
            u128::MAX
        } else {
            (1u128 << (width * 8)) - 1
        };
        check(&p, value & mask);
    }
}

#[test]
fn allocation_outlives_the_frame_that_created_it() {
    let mut p = program(
        vec![
            Op::Local { dst: 0, offset: 8 },
            Op::Call {
                function: 1,
                args: vec![],
                destination: 0,
            },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
            Op::Imm { dst: 2, value: 91 },
            Op::Store {
                address: 1,
                src: 2,
                size: 8,
            },
            Op::Local { dst: 3, offset: 0 },
            Op::Copy {
                dst: 3,
                src: 1,
                size: 8,
            },
            Op::Imm { dst: 4, value: 8 },
            Op::Deallocate {
                pointer: 1,
                size: 4,
                align: 4,
            },
            Op::Return,
        ],
        16,
        8,
    );
    p.functions.push(Function {
        name: "make".into(),
        registers: 3,
        frame_size: 8,
        frame_align: 16,
        args: vec![],
        result: Slot { offset: 0, size: 8 },
        code: vec![
            Op::Imm { dst: 0, value: 8 },
            Op::Allocate {
                dst: 1,
                size: 0,
                align: 0,
                zeroed: false,
            },
            Op::Local { dst: 2, offset: 0 },
            Op::Store {
                address: 2,
                src: 1,
                size: 8,
            },
            Op::Return,
        ],
    });
    check(&p, 91);
}

#[test]
fn heap_budget_includes_live_registers_and_stack() {
    let p = program(
        vec![
            Op::Imm { dst: 0, value: 64 },
            Op::Imm { dst: 1, value: 8 },
            Op::Allocate {
                dst: 2,
                size: 0,
                align: 1,
                zeroed: false,
            },
            Op::Local { dst: 3, offset: 0 },
            Op::Store {
                address: 3,
                src: 2,
                size: 8,
            },
            Op::Return,
        ],
        8,
        8,
    );
    // Constants + stack + registers fit; another 80 heap bytes do not.
    let got = execute_with_engine(
        &p,
        &[],
        Limits {
            memory: 200,
            ..Limits::default()
        },
        Engine::Interpreter,
    )
    .unwrap();
    assert_eq!(got.value, 0);
}

#[test]
fn heap_jit_guards_reject_invalid_ranges_and_allow_empty_dangling_access() {
    use rust_interp_bytecode::{Binary, FUNCTION_POINTER_TAG};
    for (offset, address, size, write, passes) in [
        (Some(0), 0, 16, false, true),
        (Some(16), 0, 1, false, false),
        (None, 0, 1, false, false),
        (None, FUNCTION_POINTER_TAG as u128 | 1, 1, false, false),
        (None, 1, 1, true, false),
        (None, 1 << 40, 0, false, true),
        (None, 1 << 40, 0, true, true),
    ] {
        let mut code = vec![
            Op::Imm { dst: 0, value: 16 },
            Op::Imm { dst: 1, value: 8 },
            Op::Allocate {
                dst: 2,
                size: 0,
                align: 1,
                zeroed: true,
            },
            Op::Imm { dst: 4, value: 0 },
        ];
        if let Some(offset) = offset {
            code.push(Op::Imm {
                dst: 6,
                value: offset,
            });
            code.push(Op::Binary {
                dst: 3,
                overflow: 7,
                op: Binary::Add,
                a: 2,
                b: 6,
                bits: 64,
                signed: false,
            });
        } else {
            code.push(Op::Imm {
                dst: 3,
                value: address,
            });
        }
        code.push(if write {
            Op::Store {
                address: 3,
                src: 4,
                size,
            }
        } else {
            Op::Load {
                dst: 4,
                address: 3,
                size,
            }
        });
        code.extend([
            Op::Local { dst: 5, offset: 0 },
            Op::Store {
                address: 5,
                src: 4,
                size: 8,
            },
            Op::Deallocate {
                pointer: 2,
                size: 0,
                align: 1,
            },
            Op::Return,
        ]);
        let p = program(code, 8, 8);
        let mut engines = vec![Engine::Interpreter];
        if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
            engines.push(Engine::Jit);
        }
        for engine in engines {
            let got = execute_with_engine(&p, &[], Limits::default(), engine);
            if passes {
                assert_eq!(got.unwrap().value, 0);
            } else {
                assert!(got.is_err());
            }
        }
    }
}
