use crate::control_flow::{ControlFlowReport, optimize, transform_code};
use crate::{Binary, Engine, Function, Limits, Op, Program, Slot, VERSION, execute_with_engine};

fn transform(original: &Program, layout: bool) -> Result<(Program, ControlFlowReport), String> {
    let mut output = original.clone();
    let report = optimize(&mut output, layout)?;
    let mut summary_output = original.clone();
    let summary = if layout {
        crate::optimize_control_flow_summary(&mut summary_output)?
    } else {
        crate::control_flow::optimize_impl(&mut summary_output, layout, false)?
    };
    assert_eq!(bincode::serialize(&summary_output).unwrap(), bincode::serialize(&output).unwrap());
    assert_eq!(summary.old_operations, report.old_operations);
    assert_eq!(summary.new_operations, report.new_operations);
    assert!(summary.functions.is_empty());
    let mut before = original.clone();
    let mut after = output.clone();
    for f in &mut before.functions {
        f.code.clear();
    }
    for f in &mut after.functions {
        f.code.clear();
    }
    assert_eq!(
        bincode::serialize(&before).unwrap(),
        bincode::serialize(&after).unwrap()
    );
    Ok((output, report))
}

fn engines() -> Vec<Engine> {
    let mut engines = vec![Engine::Interpreter];
    if cfg!(all(target_arch = "aarch64", target_os = "macos")) {
        engines.push(Engine::Jit);
    }
    engines
}
fn program(code: Vec<Op>) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![
            Function {
                name: "root".into(),
                frame_size: 16,
                frame_align: 8,
                registers: 7,
                args: vec![Slot { offset: 0, size: 8 }],
                result: Slot { offset: 8, size: 8 },
                code,
            },
            Function {
                name: "accumulate".into(),
                frame_size: 32,
                frame_align: 8,
                registers: 5,
                args: vec![
                    Slot {
                        offset: 16,
                        size: 8,
                    },
                    Slot {
                        offset: 24,
                        size: 8,
                    },
                ],
                result: Slot { offset: 0, size: 8 },
                code: vec![
                    Op::Local { dst: 0, offset: 16 },
                    Op::Load {
                        dst: 0,
                        address: 0,
                        size: 8,
                    },
                    Op::Local { dst: 1, offset: 24 },
                    Op::Load {
                        dst: 1,
                        address: 1,
                        size: 8,
                    },
                    Op::Imm { dst: 2, value: 17 },
                    Op::Binary {
                        dst: 1,
                        overflow: 3,
                        op: Binary::Mul,
                        a: 1,
                        b: 2,
                        bits: 64,
                        signed: false,
                    },
                    Op::Binary {
                        dst: 1,
                        overflow: 3,
                        op: Binary::Add,
                        a: 1,
                        b: 0,
                        bits: 64,
                        signed: false,
                    },
                    Op::Local { dst: 4, offset: 0 },
                    Op::Store {
                        address: 4,
                        src: 1,
                        size: 8,
                    },
                    Op::Return,
                ],
            },
        ],
    }
}

#[test]
fn loops_aliasing_calls_and_duplicate_switch_precedence_keep_values_and_budgets() {
    let p = program(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Local { dst: 1, offset: 8 },
        Op::Imm { dst: 2, value: 0 },
        Op::Store {
            address: 1,
            src: 2,
            size: 8,
        },
        Op::Jump { target: 12 },
        Op::Call {
            function: 1,
            args: vec![0, 1],
            destination: 1,
        },
        Op::Load {
            dst: 3,
            address: 0,
            size: 8,
        },
        Op::Imm { dst: 4, value: 1 },
        Op::Binary {
            dst: 3,
            overflow: 5,
            op: Binary::Sub,
            a: 3,
            b: 4,
            bits: 64,
            signed: false,
        },
        Op::Store {
            address: 0,
            src: 3,
            size: 8,
        },
        Op::Jump { target: 12 },
        Op::Trap {
            message: "second duplicate switch case must not win".into(),
        },
        Op::Load {
            dst: 6,
            address: 0,
            size: 8,
        },
        Op::Switch {
            value: 6,
            cases: vec![(0, 16), (0, 11)],
            otherwise: 14,
        },
        Op::Jump { target: 5 },
        Op::Trap {
            message: "unreachable sentinel".into(),
        },
        Op::Return,
    ]);
    for layout in [false, true] {
        let (q, _) = transform(&p, layout).unwrap();
        assert!(q.functions[0].code.len() < p.functions[0].code.len());
        for engine in engines() {
            for seed in [0u64, 1, 2, 7, 35] {
                let expected = (1..=seed)
                    .rev()
                    .fold(0u64, |a, n| a.wrapping_mul(17).wrapping_add(n));
                for program in [&p, &q] {
                    assert_eq!(
                        execute_with_engine(program, &[seed as u128], Limits::default(), engine)
                            .unwrap()
                            .value,
                        expected as u128
                    );
                }
            }
            let expected = execute_with_engine(&q, &[3], Limits::default(), engine).unwrap();
            for instructions in 0..=expected.instructions {
                let result = execute_with_engine(
                    &q,
                    &[3],
                    Limits {
                        instructions,
                        ..Limits::default()
                    },
                    engine,
                );
                if instructions == expected.instructions {
                    assert_eq!(result.unwrap().value, expected.value);
                } else {
                    assert!(result.unwrap_err().contains("instruction limit"));
                }
            }
        }
    }
}

#[test]
fn layout_removes_jumps_between_calls_without_changing_their_order() {
    let p = program(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Local { dst: 1, offset: 8 },
        Op::Call {
            function: 1,
            args: vec![0, 0],
            destination: 1,
        },
        Op::Jump { target: 7 },
        Op::Imm { dst: 2, value: 0 },
        Op::Trap {
            message: "unreachable".into(),
        },
        Op::Return,
        Op::Call {
            function: 1,
            args: vec![0, 1],
            destination: 1,
        },
        Op::Jump { target: 6 },
    ]);
    let (q, _) = transform(&p, true).unwrap();
    assert!(
        !q.functions[0]
            .code
            .iter()
            .any(|op| matches!(op, Op::Jump { .. }))
    );
    assert_eq!(
        q.functions[0]
            .code
            .iter()
            .filter(|op| matches!(op, Op::Call { .. }))
            .count(),
        2
    );
    for engine in engines() {
        for seed in [0u64, 1, 7, u64::MAX] {
            let expected = seed.wrapping_mul(307) as u128;
            assert_eq!(
                execute_with_engine(&p, &[seed as u128], Limits::default(), engine)
                    .unwrap()
                    .value,
                expected
            );
            assert_eq!(
                execute_with_engine(&q, &[seed as u128], Limits::default(), engine)
                    .unwrap()
                    .value,
                expected
            );
        }
    }
}

#[test]
fn fault_order_and_initial_zero_reads_are_preserved() {
    let p = program(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load {
            dst: 1,
            address: 0,
            size: 8,
        },
        Op::Switch {
            value: 1,
            cases: vec![(0, 7)],
            otherwise: 8,
        },
        Op::Imm {
            dst: 2,
            value: u64::MAX as u128,
        },
        Op::Load {
            dst: 3,
            address: 2,
            size: 8,
        },
        Op::Assert {
            value: 4,
            expected: true,
            message: "later assertion".into(),
        },
        Op::Jump { target: 7 },
        Op::Return,
        Op::Jump { target: 3 },
    ]);
    for layout in [false, true] {
        let (q, _) = transform(&p, layout).unwrap();
        for engine in engines() {
            assert_eq!(
                execute_with_engine(&q, &[0], Limits::default(), engine)
                    .unwrap()
                    .value,
                0
            );
            let a = execute_with_engine(&p, &[1], Limits::default(), engine).unwrap_err();
            let b = execute_with_engine(&q, &[1], Limits::default(), engine).unwrap_err();
            assert_eq!(a, b);
            assert!(!b.contains("later assertion"));
        }
    }
}

#[test]
fn cycles_and_invalid_or_terminal_fallthrough_bodies_do_not_invent_success() {
    for code in [
        vec![Op::Jump { target: 1 }, Op::Jump { target: 0 }, Op::Return],
        vec![Op::Jump { target: 1 }, Op::Jump { target: 1 }, Op::Return],
    ] {
        let p = program(code);
        for layout in [false, true] {
            let (q, _) = transform(&p, layout).unwrap();
            for engine in engines() {
                for instructions in [0, 1, 2, 17] {
                    assert!(
                        execute_with_engine(
                            &q,
                            &[0],
                            Limits {
                                instructions,
                                ..Limits::default()
                            },
                            engine
                        )
                        .unwrap_err()
                        .contains("instruction limit")
                    );
                }
            }
        }
    }
    assert!(transform_code(&[], true).is_err());
    assert!(
        transform_code(&[Op::Jump { target: 99 }], true)
            .unwrap_err()
            .contains("invalid CFG")
    );
    let p = vec![Op::Imm { dst: 0, value: 7 }];
    let (q, report) = transform_code(&p, true).unwrap();
    assert_eq!(
        bincode::serialize(&p).unwrap(),
        bincode::serialize(&q).unwrap()
    );
    assert!(report.skipped_terminal_fallthrough);
}

#[test]
fn growth_fallback_and_fresh_zeroes_survive_repeated_calls() {
    // Taking the default arm first would separate the case's implicit
    // fallthrough from the common return, adding an otherwise unnecessary jump.
    let mut p = program(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load {
            dst: 0,
            address: 0,
            size: 8,
        },
        Op::Switch {
            value: 0,
            cases: vec![(0, 3)],
            otherwise: 4,
        },
        Op::Imm { dst: 1, value: 7 },
        Op::Local { dst: 2, offset: 8 },
        Op::Store {
            address: 2,
            src: 1,
            size: 8,
        },
        Op::Return,
    ]);
    p.entry = 2;
    p.functions.push(Function {
        name: "repeat".into(),
        frame_size: 16,
        frame_align: 8,
        registers: 4,
        args: vec![],
        result: Slot { offset: 8, size: 8 },
        code: vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Local { dst: 1, offset: 8 },
            Op::Imm { dst: 2, value: 0 },
            Op::Store {
                address: 0,
                src: 2,
                size: 8,
            },
            Op::Call {
                function: 0,
                args: vec![0],
                destination: 1,
            },
            Op::Load {
                dst: 3,
                address: 1,
                size: 8,
            },
            Op::Assert {
                value: 3,
                expected: true,
                message: "first call writes seven".into(),
            },
            Op::Imm { dst: 2, value: 1 },
            Op::Store {
                address: 0,
                src: 2,
                size: 8,
            },
            Op::Call {
                function: 0,
                args: vec![0],
                destination: 1,
            },
            Op::Load {
                dst: 3,
                address: 1,
                size: 8,
            },
            Op::Assert {
                value: 3,
                expected: false,
                message: "second call reads fresh zero".into(),
            },
            Op::Return,
        ],
    });
    let (q, report) = transform(&p, true).unwrap();
    assert!(report.functions[0].layout_rejected_for_growth);
    assert_eq!(
        bincode::serialize(&p.functions[0]).unwrap(),
        bincode::serialize(&q.functions[0]).unwrap()
    );
    for engine in engines() {
        assert_eq!(
            execute_with_engine(&p, &[], Limits::default(), engine)
                .unwrap()
                .value,
            0
        );
        assert_eq!(
            execute_with_engine(&q, &[], Limits::default(), engine)
                .unwrap()
                .value,
            0
        );
    }
}

#[test]
fn straight_line_bodies_keep_complete_bytes_and_zero_reports() {
    use crate::control_flow::FunctionControlFlowReport;

    let zero_read = || Op::Assert {
        value: 6,
        expected: false,
        message: "initial zero".into(),
    };
    let trap = || Op::Trap {
        message: "straight-line sentinel".into(),
    };
    for (code, operations, zeroes) in [
        (vec![Op::Return], 1, false),
        (vec![zero_read(), Op::Return], 2, true),
        (vec![Op::Imm { dst: 6, value: 0 }, zero_read(), trap()], 3, false),
        (vec![zero_read(), trap()], 2, true),
    ] {
        let p = program(code);
        for layout in [false, true] {
            let (q, report) = transform(&p, layout).unwrap();
            assert_eq!(
                bincode::serialize(&p).unwrap(),
                bincode::serialize(&q).unwrap()
            );
            let expected = ControlFlowReport {
                functions: vec![
                    FunctionControlFlowReport {
                        function: 0,
                        old_operations: operations,
                        new_operations: operations,
                        register_zeroes_before: zeroes,
                        register_zeroes_proposed: zeroes,
                        ..Default::default()
                    },
                    FunctionControlFlowReport {
                        function: 1,
                        old_operations: 10,
                        new_operations: 10,
                        ..Default::default()
                    },
                ],
                old_operations: operations + 10,
                new_operations: operations + 10,
            };
            assert_eq!(
                bincode::serialize(&report).unwrap(),
                bincode::serialize(&expected).unwrap()
            );
        }
    }
}

#[test]
fn interior_returns_and_traps_still_remove_unreachable_operations() {
    use crate::control_flow::FunctionControlFlowReport;

    for code in [
        vec![
            Op::Return,
            Op::Imm { dst: 6, value: 7 },
            Op::Trap { message: "unreachable".into() },
        ],
        vec![
            Op::Trap { message: "first fault".into() },
            Op::Imm { dst: 6, value: 7 },
            Op::Return,
        ],
    ] {
        let p = program(code);
        let mut expected_program = p.clone();
        expected_program.functions[0].code.truncate(1);
        for layout in [false, true] {
            let (q, report) = transform(&p, layout).unwrap();
            assert_eq!(
                bincode::serialize(&q).unwrap(),
                bincode::serialize(&expected_program).unwrap()
            );
            let expected = ControlFlowReport {
                functions: vec![
                    FunctionControlFlowReport {
                        function: 0,
                        old_operations: 3,
                        new_operations: 1,
                        unreachable_operations: 2,
                        ..Default::default()
                    },
                    FunctionControlFlowReport {
                        function: 1,
                        old_operations: 10,
                        new_operations: 10,
                        ..Default::default()
                    },
                ],
                old_operations: 13,
                new_operations: 11,
            };
            assert_eq!(
                bincode::serialize(&report).unwrap(),
                bincode::serialize(&expected).unwrap()
            );
        }
    }
}

#[test]
fn malformed_later_function_is_rejected_before_any_cfg_mutation() {
    let mut p = program(vec![Op::Return]);
    p.functions[1].code = vec![
        Op::Return,
        Op::Imm { dst: 4, value: 7 },
        Op::Trap { message: "valid unreachable body".into() },
    ];
    let mut invalid = p.functions[1].clone();
    invalid.name = "invalid later function".into();
    // All functions are validated, even registers in unreachable operations.
    // The valid middle body would shrink if mutation began before validation.
    invalid.code = vec![
        Op::Return,
        Op::Imm { dst: 5, value: 7 },
        Op::Trap { message: "invalid unreachable body".into() },
    ];
    p.functions.push(invalid);
    let expected = bincode::serialize(&p).unwrap();
    for layout in [false, true] {
        let mut q = p.clone();
        assert_eq!(optimize(&mut q, layout).unwrap_err(), "invalid register");
        assert_eq!(bincode::serialize(&q).unwrap(), expected);
        let mut summary_output = p.clone();
        let error = if layout {
            crate::optimize_control_flow_summary(&mut summary_output).unwrap_err()
        } else {
            crate::control_flow::optimize_impl(&mut summary_output, layout, false).unwrap_err()
        };
        assert_eq!(error, "invalid register");
        assert_eq!(bincode::serialize(&summary_output).unwrap(), expected);
    }
}
