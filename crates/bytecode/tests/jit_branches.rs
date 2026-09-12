#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{
    Engine, Function, Limits, Op, Program, Slot, VERSION, execute_with_engine,
};

fn branches(values: &[u128]) -> Program {
    let mut code = vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load {
            dst: 1,
            address: 0,
            size: 16,
        },
        Op::Switch {
            value: 1,
            cases: values
                .iter()
                .enumerate()
                .map(|(i, v)| (*v, 3 + 4 * i))
                .collect(),
            otherwise: 3 + 4 * values.len(),
        },
    ];
    for index in 0..=values.len() {
        code.extend([
            Op::Imm {
                dst: 2,
                value: index as u128 + 11,
            },
            Op::Local { dst: 0, offset: 16 },
            Op::Store {
                address: 0,
                src: 2,
                size: 16,
            },
            Op::Return,
        ]);
    }
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![Function {
            name: "branch-table".into(),
            frame_size: 32,
            frame_align: 16,
            registers: 3,
            args: vec![Slot {
                offset: 0,
                size: 16,
            }],
            result: Slot {
                offset: 16,
                size: 16,
            },
            code,
        }],
    }
}

#[test]
fn branch_exits_compare_all_128_bits_and_retain_first_match() {
    let p = branches(&[0, 1 << 64, 1 << 64, u128::MAX]);
    for (input, want) in [
        (0, 11),
        (1 << 64, 12),
        (u128::MAX, 14),
        (1, 15),
        (u64::MAX as u128, 15),
    ] {
        for engine in [Engine::Interpreter, Engine::Jit] {
            let result = execute_with_engine(&p, &[input], Limits::default(), engine).unwrap();
            assert_eq!(result.value, want);
            assert_eq!(result.instructions, 7);
            if engine == Engine::Jit {
                assert_eq!(result.jit_instructions, 6);
            }
            for budget in 0..=8 {
                let result = execute_with_engine(
                    &p,
                    &[input],
                    Limits {
                        instructions: budget,
                        ..Limits::default()
                    },
                    engine,
                );
                if budget >= 7 {
                    assert_eq!(result.unwrap().value, want);
                } else {
                    assert!(result.unwrap_err().contains("instruction limit"));
                }
            }
        }
    }
}

#[test]
fn large_switch_fallback_and_empty_switch_preserve_behavior() {
    for values in [vec![], (0..17u128).collect()] {
        let p = branches(&values);
        for input in [0, 1, 16, 17, u128::MAX] {
            let want = values
                .iter()
                .position(|v| *v == input)
                .unwrap_or(values.len()) as u128
                + 11;
            for engine in [Engine::Interpreter, Engine::Jit] {
                let result = execute_with_engine(&p, &[input], Limits::default(), engine).unwrap();
                assert_eq!(result.value, want);
                assert_eq!(result.instructions, 7);
            }
        }
    }
}

#[test]
fn compiled_backedges_keep_running_until_the_instruction_budget() {
    for terminal in [
        Op::Jump { target: 0 },
        Op::Switch {
            value: 0,
            cases: vec![(0, 0)],
            otherwise: 3,
        },
    ] {
        let mut p = branches(&[]);
        p.functions[0].code = vec![
            Op::Imm { dst: 0, value: 0 },
            Op::Imm { dst: 1, value: 1 },
            terminal,
            Op::Return,
        ];
        for budget in [1, 2, 3, 4, 17, 1001] {
            for engine in [Engine::Interpreter, Engine::Jit] {
                let result = execute_with_engine(
                    &p,
                    &[0],
                    Limits {
                        instructions: budget,
                        ..Limits::default()
                    },
                    engine,
                );
                assert!(result.unwrap_err().contains("instruction limit"));
            }
        }
    }
}
