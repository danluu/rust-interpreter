#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{
    Binary, Engine, FUNCTION_POINTER_TAG, Function, Limits, Op, Program, Slot, VERSION,
    execute_profiled, execute_with_engine,
};

fn fixture(indirect: bool) -> Program {
    let mut root = Function {
        name: "entry".into(),
        frame_size: 16,
        frame_align: 16,
        registers: 4,
        args: vec![Slot { offset: 0, size: 8 }],
        result: Slot { offset: 0, size: 8 },
        code: vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Imm {
                dst: 1,
                value: (FUNCTION_POINTER_TAG | 2) as u128,
            },
            Op::Imm { dst: 2, value: 42 },
        ],
    };
    let call = if indirect {
        Op::CallIndirect {
            callee: 1,
            args: vec![0],
            arg_sizes: vec![8],
            destination: 0,
            result_size: 8,
        }
    } else {
        Op::Call {
            function: 1,
            args: vec![0],
            destination: 0,
        }
    };
    root.code.extend([call.clone(), call, Op::Return]);
    let recursive = Function {
        name: "recursive".into(),
        frame_size: 16,
        frame_align: 16,
        registers: 4,
        args: vec![Slot { offset: 0, size: 8 }],
        result: Slot { offset: 0, size: 8 },
        code: vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
            Op::Switch {
                value: 1,
                cases: vec![(0, 8)],
                otherwise: 3,
            },
            Op::Imm { dst: 2, value: 1 },
            Op::Binary {
                dst: 1,
                overflow: 3,
                a: 1,
                b: 2,
                op: Binary::Sub,
                bits: 64,
                signed: false,
            },
            Op::Store {
                address: 0,
                src: 1,
                size: 8,
            },
            Op::Call {
                function: 1,
                args: vec![0],
                destination: 0,
            },
            Op::Return,
            Op::Return,
        ],
    };
    let mut unused = recursive.clone();
    unused.name = "unused".into();
    unused.code = (0..100_000).map(|n| Op::Imm { dst: 0, value: n }).collect();
    unused.code.push(Op::Return);
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![root, recursive, unused],
    }
}

#[test]
fn lazy_recursion_indirect_calls_and_code_declines_preserve_all_logical_work() {
    for indirect in [false, true] {
        let p = fixture(indirect);
        let (expected, reference) =
            execute_profiled(&p, &[4], Limits::default(), Engine::Interpreter).unwrap();
        for capacity in [0, 1, 128, 256, 1024, 16 * 1024 * 1024] {
            let limits = || Limits {
                jit_code_bytes: capacity,
                ..Limits::default()
            };
            let ordinary = execute_with_engine(&p, &[4], limits(), Engine::Jit).unwrap();
            let (observed, profile) = execute_profiled(&p, &[4], limits(), Engine::Jit).unwrap();
            assert_eq!(ordinary.value, 0);
            assert_eq!(observed.value, 0);
            assert_eq!(ordinary.instructions, expected.instructions);
            assert_eq!(observed.instructions, expected.instructions);
            assert!(ordinary.jit_bytes <= capacity);
            assert!(observed.jit_bytes <= capacity);
            assert_eq!(
                ordinary.jit_compiled_functions + ordinary.jit_declined_functions,
                2
            );
            assert_eq!(
                observed.jit_compiled_functions + observed.jit_declined_functions,
                2
            );
            if capacity == 0 {
                assert_eq!(ordinary.jit_instructions, 0);
                assert_eq!(ordinary.jit_declined_functions, 2);
            }
            for (actual, expected) in profile.functions.iter().zip(&reference.functions) {
                let mut counts = actual.interpreted.clone();
                for (pc, hits) in actual
                    .jit_blocks
                    .iter()
                    .enumerate()
                    .filter(|(_, n)| **n != 0)
                {
                    for n in &mut counts[pc..actual.jit_block_ends[pc]] {
                        *n += hits;
                    }
                }
                assert_eq!(counts, expected.interpreted);
            }
            assert!(profile.functions[2].jit_block_ends.iter().all(|n| *n == 0));
            for instructions in [0, 1, 6, expected.instructions - 1, expected.instructions] {
                let result = execute_with_engine(
                    &p,
                    &[4],
                    Limits {
                        jit_code_bytes: capacity,
                        instructions,
                        ..Limits::default()
                    },
                    Engine::Jit,
                );
                if instructions == expected.instructions {
                    assert_eq!(result.unwrap().value, 0);
                } else {
                    assert_eq!(
                        result.unwrap_err(),
                        "interpreter instruction limit exceeded"
                    );
                }
            }
        }
    }
}

#[test]
fn unused_functions_are_still_validated_with_zero_native_budget() {
    let mut p = fixture(false);
    p.functions[2].code[0] = Op::Jump { target: usize::MAX };
    for engine in [Engine::Interpreter, Engine::Jit] {
        assert!(
            execute_with_engine(
                &p,
                &[1],
                Limits {
                    jit_code_bytes: 0,
                    ..Limits::default()
                },
                engine
            )
            .is_err()
        );
    }
}

#[test]
fn declined_native_regions_preserve_guest_faults() {
    for fault in [
        Op::Assert {
            value: 1,
            expected: false,
            message: "expected failure".into(),
        },
        Op::Binary {
            dst: 2,
            overflow: 3,
            a: 1,
            b: 0,
            op: Binary::Div,
            bits: 64,
            signed: false,
        },
    ] {
        let mut p = fixture(false);
        p.functions[0].code = vec![
            Op::Imm { dst: 0, value: 0 },
            Op::Imm { dst: 1, value: 1 },
            fault,
            Op::Return,
        ];
        let expected =
            execute_with_engine(&p, &[1], Limits::default(), Engine::Interpreter).unwrap_err();
        for capacity in [0, 16, 16 * 1024 * 1024] {
            assert_eq!(
                execute_with_engine(
                    &p,
                    &[1],
                    Limits {
                        jit_code_bytes: capacity,
                        ..Limits::default()
                    },
                    Engine::Jit
                )
                .unwrap_err(),
                expected
            );
        }
    }
}
