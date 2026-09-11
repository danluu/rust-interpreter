#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{
    Binary, Engine, Function, Limits, Op, Program, Slot, Unary, VERSION, execute,
    execute_with_engine,
};

fn machine(operation: Op) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![], thread_locals: vec![],
        functions: vec![Function {
            name: "scalar".into(),
            frame_size: 48,
            frame_align: 16,
            registers: 7,
            args: vec![
                Slot {
                    offset: 0,
                    size: 16,
                },
                Slot {
                    offset: 16,
                    size: 16,
                },
            ],
            result: Slot {
                offset: 32,
                size: 16,
            },
            code: vec![
                Op::Local { dst: 0, offset: 0 },
                Op::Local { dst: 1, offset: 16 },
                Op::Load {
                    dst: 2,
                    address: 0,
                    size: 16,
                },
                Op::Load {
                    dst: 3,
                    address: 1,
                    size: 16,
                },
                operation,
                Op::Local { dst: 6, offset: 32 },
                Op::Store {
                    address: 6,
                    src: 4,
                    size: 16,
                },
                Op::Return,
            ],
        }],
    }
}
fn agrees(program: &Program, a: u128, b: u128) {
    let interpreted = execute(program, &[a, b], Limits::default()).unwrap();
    let native = execute_with_engine(program, &[a, b], Limits::default(), Engine::Jit).unwrap();
    assert_eq!(
        native.value, interpreted.value,
        "{:?}; a={a:x}, b={b:x}",
        program.functions[0].code
    );
    assert_eq!(native.instructions, interpreted.instructions);
    assert!(native.jit_instructions > 0);
}

#[test]
fn scalar_sequences_match_the_interpreter() {
    for bits in [8, 16, 32, 64] {
        for signed in [false, true] {
            for op in [
                Binary::Add,
                Binary::Sub,
                Binary::Mul,
                Binary::And,
                Binary::Or,
                Binary::Xor,
                Binary::Shl,
                Binary::Shr,
                Binary::RotateLeft,
                Binary::RotateRight,
                Binary::Eq,
                Binary::Ne,
                Binary::Lt,
                Binary::Le,
                Binary::Gt,
                Binary::Ge,
                Binary::Cmp,
            ] {
                let p = machine(Op::Binary {
                    dst: 4,
                    overflow: 5,
                    op,
                    a: 2,
                    b: 3,
                    bits,
                    signed,
                });
                for (a, b) in [
                    (0, 0),
                    (0, 1),
                    (1, 0),
                    (u128::MAX, 1),
                    (1, u128::MAX),
                    (0x0123456789abcdef, 0xfedcba9876543210),
                    (1u128 << (bits - 1), 3),
                    (1u128 << (bits - 1), u128::MAX),
                    (u128::MAX, u128::MAX),
                    (128, 127),
                    (256, 129),
                ] {
                    agrees(&p, a, b);
                }
            }
        }
        for op in [
            Unary::Not,
            Unary::Neg,
            Unary::LeadingZeros,
            Unary::TrailingZeros,
            Unary::SwapBytes,
        ] {
            let p = machine(Op::Unary {
                dst: 4,
                op,
                src: 2,
                bits,
            });
            for a in [0, 1, 128, 256, u128::MAX, 0x123456789abcdef0] {
                agrees(&p, a, 0);
            }
        }
    }
    for from in [8, 16, 32, 64, 128] {
        for to in [8, 16, 32, 64, 128] {
            for signed in [false, true] {
                let p = machine(Op::Cast {
                    dst: 4,
                    src: 2,
                    from,
                    to,
                    signed,
                });
                for a in [
                    0,
                    127,
                    128,
                    u64::MAX as u128,
                    u128::MAX,
                    1u128 << (from - 1),
                ] {
                    agrees(&p, a, 0);
                }
            }
        }
    }
}

#[test]
fn memory_widths_and_overlapping_copies_match() {
    for size in 0..=16 {
        let mut p = machine(Op::Load {
            dst: 4,
            address: 1,
            size,
        });
        p.functions[0].code[6] = Op::Store {
            address: 6,
            src: 4,
            size,
        };
        agrees(&p, u128::MAX, 0xfedcba98765432100123456789abcdef);
    }
    for size in 0..=32 {
        let mut p = machine(Op::Copy {
            dst: 1,
            src: 0,
            size,
        });
        p.functions[0].frame_size = 64;
        p.functions[0].code = vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Local { dst: 1, offset: 3 },
            Op::Copy {
                dst: 1,
                src: 0,
                size,
            },
            Op::Local { dst: 6, offset: 32 },
            Op::Load {
                dst: 4,
                address: 1,
                size: 16,
            },
            Op::Store {
                address: 6,
                src: 4,
                size: 16,
            },
            Op::Return,
        ];
        agrees(&p, 0xfedcba98765432100123456789abcdef, u128::MAX);
    }
}

#[test]
fn folded_addresses_preserve_widths_and_reject_out_of_frame_accesses() {
    for offset in [8, (1u128 << 100) | 8, 41] {
        let mut p = machine(Op::Return);
        p.functions[0].code = vec![
            Op::Local {dst: 0,offset: 0},
            Op::Imm {dst: 2,value: offset},
            Op::Binary {dst: 0,overflow: 5,op: Binary::Add,a: 0,b: 2,bits: 64,signed: false},
            Op::Load {dst: 4,address: 0,size: 8},
            Op::Local {dst: 6,offset: 32},
            Op::Store {address: 6,src: 4,size: 16},
            Op::Return,
        ];
        for engine in [Engine::Interpreter,Engine::Jit] {
            let got = execute_with_engine(&p,&[u128::MAX,0],Limits::default(),engine);
            if offset == 41 {assert!(got.is_err());}
            else {assert_eq!(got.unwrap().value,u64::MAX as u128);}
        }
    }
    for replace in [Op::Imm {dst: 0,value: 0},Op::Load {dst: 0,address: 1,size: 8}] {
        let mut p = machine(Op::Return);
        p.functions[0].code = vec![
            Op::Local {dst: 0,offset: 0},
            Op::Local {dst: 1,offset: 16},
            replace,
            Op::Load {dst: 4,address: 0,size: 8},
            Op::Local {dst: 6,offset: 32},
            Op::Store {address: 6,src: 4,size: 16},
            Op::Return,
        ];
        for engine in [Engine::Interpreter,Engine::Jit] {
            assert!(execute_with_engine(&p,&[17,4096],Limits::default(),engine).is_err());
        }
    }
}

#[test]
fn known_values_are_flushed_for_loop_carried_reads_and_branch_joins() {
    let mut p = machine(Op::Return);
    p.functions[0].code = vec![
        Op::Local {dst: 0,offset: 32},
        Op::Imm {dst: 1,value: 2},
        Op::Imm {dst: 2,value: 3},
        Op::Jump {target: 4},
        // The read and replacement of r2 are in the same native region. Its
        // final value must reach the next entry through the loop's backedge.
        Op::Store {address: 0,src: 2,size: 16},
        Op::Imm {dst: 2,value: 99},
        Op::Imm {dst: 3,value: 1},
        Op::Binary {dst: 1,overflow: 5,op: Binary::Sub,a: 1,b: 3,bits: 64,signed: false},
        Op::Switch {value: 1,cases: vec![(0,9)],otherwise: 4},
        Op::Return,
    ];
    for engine in [Engine::Interpreter,Engine::Jit] {
        assert_eq!(execute_with_engine(&p,&[0,0],Limits::default(),engine).unwrap().value,99);
    }
    p.functions[0].code = vec![
        Op::Local {dst: 0,offset: 0},
        Op::Load {dst: 1,address: 0,size: 16},
        Op::Switch {value: 1,cases: vec![(0,3)],otherwise: 8},
        Op::Local {dst: 2,offset: 16},
        Op::Imm {dst: 3,value: 0},
        Op::Imm {dst: 4,value: 0},
        Op::Jump {target: 13},
        Op::Trap {message: "unreachable".into()},
        Op::Imm {dst: 2,value: 1},
        Op::Imm {dst: 3,value: 0},
        Op::Imm {dst: 4,value: 0},
        Op::Jump {target: 13},
        Op::Trap {message: "unreachable".into()},
        Op::Store {address: 2,src: 3,size: 1},
        Op::Load {dst: 4,address: 2,size: 16},
        Op::Local {dst: 6,offset: 32},
        Op::Store {address: 6,src: 4,size: 16},
        Op::Return,
    ];
    for engine in [Engine::Interpreter,Engine::Jit] {
        assert_eq!(execute_with_engine(&p,&[0,u128::MAX],Limits::default(),engine).unwrap().value,u128::MAX-255);
        assert!(execute_with_engine(&p,&[1,u128::MAX],Limits::default(),engine).is_err());
    }
}

#[test]
fn memory_faults_and_instruction_limits_still_stop_execution() {
    for address in [0, u64::MAX as u128, 4096] {
        let mut p = machine(Op::Load {
            dst: 4,
            address: 0,
            size: 8,
        });
        p.functions[0].code[0] = Op::Imm {
            dst: 0,
            value: address,
        };
        assert!(execute_with_engine(&p, &[0, 0], Limits::default(), Engine::Jit).is_err());
    }
    let p = machine(Op::Binary {
        dst: 4,
        overflow: 5,
        op: Binary::Add,
        a: 2,
        b: 3,
        bits: 64,
        signed: false,
    });
    for instructions in 0..8 {
        let native = execute_with_engine(
            &p,
            &[1, 2],
            Limits {
                instructions,
                ..Limits::default()
            },
            Engine::Jit,
        );
        let interpreted = execute(
            &p,
            &[1, 2],
            Limits {
                instructions,
                ..Limits::default()
            },
        );
        assert_eq!(native.is_ok(), interpreted.is_ok());
    }
}

#[test]
fn large_straight_line_regions_preserve_results_faults_and_budgets() {
    // This sequence previously placed its first memory-check branch more
    // than 1 MiB away from the shared failure return, as Ruff's registry did.
    // Odd-width copies exercise the emitter's longest byte-assembly path.
    let mut p = machine(Op::Return);
    p.functions[0].frame_size = 64;
    let code = &mut p.functions[0].code;
    *code = vec![Op::Local { dst: 0, offset: 0 }, Op::Local { dst: 1, offset: 16 }];
    code.extend((0..12_000).map(|_| Op::Copy { dst: 1, src: 0, size: 31 }));
    code.push(Op::Return);
    agrees(&p, 0xfedcba98765432100123456789abcdef, u128::MAX);
    let compiled = execute_with_engine(&p, &[1, 2], Limits::default(), Engine::Jit).unwrap();
    assert!(compiled.jit_bytes > 1024 * 1024);
    assert!(compiled.jit_instructions > 11_000);
    for at in [2, 1026, 11_999] {
        let mut invalid = p.clone();
        invalid.functions[0].code[at] = Op::Imm { dst: 0, value: 0 };
        assert!(execute(&invalid, &[1, 2], Limits::default()).is_err());
        let error = execute_with_engine(&invalid, &[1, 2], Limits::default(), Engine::Jit).unwrap_err();
        assert!(error.contains("memory access"), "{error}");
    }
    for instructions in [500, 1024, 1025, 2049, 12_002] {
        assert!(execute(&p, &[1, 2], Limits { instructions, ..Limits::default() }).is_err());
        let error = execute_with_engine(&p, &[1, 2], Limits { instructions, ..Limits::default() }, Engine::Jit).unwrap_err();
        assert!(error.contains("instruction limit"), "{error}");
    }
}
