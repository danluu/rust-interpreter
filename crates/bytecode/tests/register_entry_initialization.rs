use rust_interp_bytecode::{
    Binary, Engine, Function, Limits, Op, Program, Slot, VERSION, execute_profiled,
    execute_with_engine,
};

#[test]
fn reused_callee_registers_keep_entry_definitions_and_real_initial_zeroes() {
    let seed = 0xfedcba98765432100123456789abcdefu128;
    for initialized in [false, true] {
        for condition in [0, 1] {
            let entry = Function {
                name: "caller".into(),
                frame_size: 32,
                frame_align: 16,
                registers: 2,
                args: vec![],
                result: Slot {
                    offset: 0,
                    size: 16,
                },
                code: vec![
                    Op::Local { dst: 0, offset: 0 },
                    Op::Local { dst: 1, offset: 16 },
                    Op::Call {
                        function: 2,
                        args: vec![],
                        destination: 1,
                    },
                    Op::Call {
                        function: 1,
                        args: vec![],
                        destination: 0,
                    },
                    Op::Return,
                ],
            };
            let callee = Function {
                name: "join-callee".into(),
                frame_size: 16,
                frame_align: 16,
                registers: 9,
                args: vec![],
                result: Slot {
                    offset: 0,
                    size: 16,
                },
                code: vec![
                    if initialized {
                        Op::Imm {
                            dst: 0,
                            value: seed,
                        }
                    } else {
                        Op::Imm {
                            dst: 7,
                            value: seed,
                        }
                    },
                    Op::Imm {
                        dst: 2,
                        value: condition,
                    },
                    Op::Switch {
                        value: 2,
                        cases: vec![(0, 6)],
                        otherwise: 3,
                    },
                    Op::Imm {
                        dst: 3,
                        value: 0xabc,
                    },
                    Op::Binary {
                        dst: 0,
                        overflow: 4,
                        op: Binary::Xor,
                        a: 0,
                        b: 3,
                        bits: 128,
                        signed: false,
                    },
                    Op::Jump { target: 6 },
                    Op::Local { dst: 1, offset: 0 },
                    Op::Store {
                        address: 1,
                        src: 0,
                        size: 16,
                    },
                    Op::Return,
                ],
            };
            let mut poison: Vec<_> = (0..128)
                .map(|dst| Op::Imm {
                    dst,
                    value: u128::MAX,
                })
                .collect();
            poison.push(Op::Return);
            let poison = Function {
                name: "poison-reused-registers".into(),
                frame_size: 0,
                frame_align: 16,
                registers: 128,
                args: vec![],
                result: Slot { offset: 0, size: 0 },
                code: poison,
            };
            let p = Program {
                version: VERSION,
                target: "aarch64-apple-darwin".into(),
                entry: 0,
                functions: vec![entry, callee, poison],
                data: vec![],
                statics: vec![],
                thread_locals: vec![],
            };
            let expected =
                (if initialized { seed } else { 0 }) ^ (if condition != 0 { 0xabc } else { 0 });
            let mut engines = vec![Engine::Interpreter];
            if cfg!(all(target_arch = "aarch64", target_os = "macos")) {
                engines.push(Engine::Jit);
            }
            for engine in engines {
                for capacity in [0, 16 * 1024 * 1024] {
                    let limits = || Limits {
                        jit_code_bytes: capacity,
                        ..Limits::default()
                    };
                    let r = execute_with_engine(&p, &[], limits(), engine).unwrap();
                    assert_eq!(r.value, expected);
                    let (observed, _) = execute_profiled(&p, &[], limits(), engine).unwrap();
                    assert_eq!(
                        (observed.value, observed.instructions),
                        (r.value, r.instructions)
                    );
                    for budget in [0, r.instructions - 1, r.instructions] {
                        let r = execute_with_engine(
                            &p,
                            &[],
                            Limits {
                                instructions: budget,
                                ..limits()
                            },
                            engine,
                        );
                        if budget < observed.instructions {
                            assert_eq!(r.unwrap_err(), "interpreter instruction limit exceeded");
                        } else {
                            assert_eq!(r.unwrap().value, expected);
                        }
                    }
                }
            }
        }
    }
}
