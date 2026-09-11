#![cfg(all(target_arch = "aarch64", target_os = "macos"))]

use rust_interp_bytecode::{Binary, Engine, Function, Limits, Op, Program, Slot,
    Unary, VERSION, execute_profiled, execute_with_engine};

fn function(name: &str, code: Vec<Op>, args: Vec<Slot>) -> Function {
    Function { name: name.into(), frame_size: 48, frame_align: 16, registers: 5,
        args, result: Slot { offset: 0, size: 16 }, code }
}

fn program(functions: Vec<Function>) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 64], statics: vec![], thread_locals: vec![], functions }
}

#[test]
fn native_exits_dispatch_calls_returns_and_short_regions_with_exact_budgets() {
    for input in [0, 1, u128::MAX, 1 << 127, 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef] {
        let p = program(vec![
            function("caller", vec![
                Op::Imm { dst: 0, value: input },
                Op::Local { dst: 1, offset: 16 },
                Op::Store { address: 1, src: 0, size: 16 },
                Op::Local { dst: 2, offset: 0 },
                Op::Call { function: 1, args: vec![1], destination: 2 },
                Op::Local { dst: 3, offset: 0 },
                Op::Load { dst: 4, address: 3, size: 16 },
                Op::Unary { dst: 4, src: 4, bits: 128, op: Unary::Not },
                Op::Store { address: 3, src: 4, size: 16 },
                Op::Return,
            ], vec![]),
            function("callee", vec![
                Op::Local { dst: 0, offset: 16 },
                Op::Load { dst: 1, address: 0, size: 16 },
                Op::Unary { dst: 1, src: 1, bits: 128, op: Unary::Not },
                Op::Local { dst: 2, offset: 0 },
                Op::Store { address: 2, src: 1, size: 16 },
                Op::Imm { dst: 3, value: 11 },
                Op::Return,
            ], vec![Slot { offset: 16, size: 16 }]),
        ]);
        for budget in 0..=18 {
            for engine in [Engine::Interpreter, Engine::Jit] {
                let limits = || Limits { instructions: budget, ..Limits::default() };
                let normal = execute_with_engine(&p, &[], limits(), engine);
                let observed = execute_profiled(&p, &[], limits(), engine);
                if budget < 17 {
                    assert_eq!(normal.unwrap_err(), "interpreter instruction limit exceeded");
                    assert_eq!(observed.unwrap_err(), "interpreter instruction limit exceeded");
                } else {
                    let normal = normal.unwrap();
                    let (observed, profile) = observed.unwrap();
                    assert_eq!(normal.value, input);
                    assert_eq!(observed.value, input);
                    assert_eq!(normal.instructions, 17);
                    assert_eq!(observed.instructions, 17);
                    assert_eq!(normal.peak_memory, observed.peak_memory);
                    assert_eq!(normal.jit_instructions, observed.jit_instructions);
                    assert_eq!(profile.functions[0].interpreted[4], 1);
                    assert_eq!(profile.functions[1].interpreted[6], 1);
                    if engine == Engine::Jit {
                        assert_eq!(normal.jit_entries, 2);
                        assert_eq!(normal.jit_instructions, 7);
                    }
                }
            }
        }
    }
}

#[test]
fn exhausted_native_regions_cannot_execute_a_following_return_or_fault() {
    for continuation in [
        Some(Op::Return),
        Some(Op::Trap { message: "continuation fault".into() }),
        Some(Op::Binary { dst: 3, overflow: 4, a: 0, b: 1,
            bits: 128, signed: false, op: Binary::Div }),
        Some(Op::CallIndirect { callee: 0, args: vec![], arg_sizes: vec![],
            destination: 2, result_size: 0 }),
        None, // A missing terminator must not hide an exhausted instruction budget.
    ] {
        let mut code = vec![
            Op::Imm { dst: 0, value: 1 },
            Op::Imm { dst: 1, value: 0 },
            Op::Local { dst: 2, offset: 0 },
        ];
        if let Some(continuation) = continuation { code.extend([continuation, Op::Return]); }
        let p = program(vec![function("budget_or_fault", code, vec![])]);
        for budget in 0..=6 {
            let limits = || Limits { instructions: budget, ..Limits::default() };
            let reference = execute_with_engine(&p, &[], limits(), Engine::Interpreter);
            if budget <= 3 {
                assert_eq!(reference.as_ref().unwrap_err(), "interpreter instruction limit exceeded");
            }
            for engine in [Engine::Interpreter, Engine::Jit] {
                for actual in [execute_with_engine(&p, &[], limits(), engine),
                    execute_profiled(&p, &[], limits(), engine).map(|(execution, _)| execution)] {
                    match (&reference, actual) {
                        (Ok(expected), Ok(actual)) => {
                            assert_eq!(expected.value, actual.value);
                            assert_eq!(expected.instructions, actual.instructions);
                        }
                        (Err(expected), Err(actual)) => assert_eq!(*expected, actual),
                        (expected, actual) => panic!("different outcome: {expected:?} / {actual:?}"),
                    }
                }
            }
        }
    }
}
