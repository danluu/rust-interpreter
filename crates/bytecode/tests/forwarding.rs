use rust_interp_bytecode::{
    Binary, Engine, FUNCTION_POINTER_TAG, Function, LeafInlineOptions, Limits, Op, Program, Slot,
    VERSION, eliminate_direct_forwarders, execute_with_engine, inline_leaves, optimize_calls,
};

fn engines() -> Vec<Engine> {
    let mut values = vec![Engine::Interpreter];
    if cfg!(all(target_arch = "aarch64", target_os = "macos")) {
        values.push(Engine::Jit);
    }
    values
}
fn chain(wrappers: usize) -> Program {
    let mut functions = Vec::new();
    for id in 0..=wrappers {
        let code = if id < wrappers {
            vec![
                Op::Local { dst: 0, offset: 16 },
                Op::Local { dst: 1, offset: 0 },
                Op::Call {
                    function: id + 1,
                    args: vec![0],
                    destination: 1,
                },
                Op::Return,
            ]
        } else {
            vec![
                Op::Local { dst: 0, offset: 16 },
                Op::Load {
                    dst: 0,
                    address: 0,
                    size: 8,
                },
                Op::Imm { dst: 1, value: 79 },
                Op::Binary {
                    dst: 0,
                    overflow: 3,
                    op: Binary::Xor,
                    a: 0,
                    b: 1,
                    bits: 64,
                    signed: false,
                },
                Op::Local { dst: 2, offset: 0 },
                Op::Store {
                    address: 2,
                    src: 0,
                    size: 8,
                },
                Op::Return,
            ]
        };
        functions.push(Function {
            name: format!("function-{id}"),
            frame_size: 32,
            frame_align: 16,
            registers: 4,
            args: vec![Slot {
                offset: 16,
                size: 8,
            }],
            result: Slot { offset: 0, size: 8 },
            code,
        });
    }
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions,
    }
}
fn unchanged_layouts(before: &Program, after: &Program) {
    let mut before = before.clone();
    let mut after = after.clone();
    for (a, b) in before.functions.iter_mut().zip(&mut after.functions) {
        assert_eq!(a.code.len(), b.code.len());
        a.code.clear();
        b.code.clear();
    }
    assert_eq!(
        bincode::serialize(&before).unwrap(),
        bincode::serialize(&after).unwrap()
    );
}

#[test]
fn forwarding_preserves_values_aliases_and_exact_resulting_budgets() {
    for alias in [false, true] {
        let mut original = chain(4);
        if alias {
            original.functions[0].code[2] = Op::Call {
                function: 1,
                args: vec![0],
                destination: 0,
            };
            original.functions[0].code.insert(
                3,
                Op::Copy {
                    dst: 1,
                    src: 0,
                    size: 8,
                },
            );
        }
        let mut optimized = original.clone();
        let report = eliminate_direct_forwarders(&mut optimized).unwrap();
        assert_eq!(report.retargeted_calls, 3);
        unchanged_layouts(&original, &optimized);
        for engine in engines() {
            for seed in [0, 7, 255, 1 << 63, u64::MAX as u128] {
                let before =
                    execute_with_engine(&original, &[seed], Limits::default(), engine).unwrap();
                let after = execute_with_engine(
                    &optimized,
                    &[seed],
                    Limits {
                        frames: 2,
                        ..Limits::default()
                    },
                    engine,
                )
                .unwrap();
                assert_eq!(before.value, seed ^ 79);
                assert_eq!(after.value, before.value);
                assert_eq!(before.instructions - after.instructions, 12);
                assert!(
                    execute_with_engine(
                        &original,
                        &[seed],
                        Limits {
                            frames: 2,
                            ..Limits::default()
                        },
                        engine
                    )
                    .unwrap_err()
                    .contains("call-depth limit")
                );
                for instructions in 0..=after.instructions {
                    let result = execute_with_engine(
                        &optimized,
                        &[seed],
                        Limits {
                            instructions,
                            ..Limits::default()
                        },
                        engine,
                    );
                    if instructions == after.instructions {
                        assert_eq!(result.unwrap().value, before.value);
                    } else {
                        assert!(result.unwrap_err().contains("instruction limit"));
                    }
                }
            }
        }
    }
}

#[test]
fn aggregate_and_zero_sized_arguments_and_results_are_copied_completely() {
    for size in [0, 1, 8, 16, 33, 64, 128] {
        let mut p = chain(2);
        for f in &mut p.functions {
            f.frame_size = 512;
            f.registers = 8;
            f.args = vec![Slot { offset: 256, size }];
            f.result = Slot { offset: 0, size };
            f.code[0] = Op::Local {
                dst: 0,
                offset: 256,
            };
        }
        p.functions[2].code = vec![
            Op::Local {
                dst: 0,
                offset: 256,
            },
            Op::Local { dst: 1, offset: 0 },
            Op::Copy {
                dst: 1,
                src: 0,
                size,
            },
            Op::Return,
        ];
        p.data.extend((0..size).map(|i| (i * 43 + 11) as u8));
        let root = &mut p.functions[0];
        root.args.clear();
        root.result.size = 0;
        root.code = vec![
            Op::Local {
                dst: 0,
                offset: 256,
            },
            Op::Imm { dst: 2, value: 16 },
            Op::Copy {
                dst: 0,
                src: 2,
                size,
            },
            Op::Local { dst: 1, offset: 0 },
            Op::Call {
                function: 1,
                args: vec![0],
                destination: 1,
            },
            Op::Imm {
                dst: 3,
                value: size as u128,
            },
            Op::CompareBytes {
                dst: 4,
                left: 1,
                right: 2,
                size: 3,
            },
            Op::Assert {
                value: 4,
                expected: false,
                message: "complete forwarded aggregate".into(),
            },
            Op::Return,
        ];
        let original = p.clone();
        assert_eq!(
            eliminate_direct_forwarders(&mut p)
                .unwrap()
                .retargeted_calls,
            1
        );
        unchanged_layouts(&original, &p);
        for engine in engines() {
            execute_with_engine(&original, &[], Limits::default(), engine).unwrap();
            execute_with_engine(&p, &[], Limits::default(), engine).unwrap();
        }
    }
}

#[test]
fn only_exact_forwarding_without_other_work_or_ambiguous_layouts_is_eligible() {
    for variant in 0..8 {
        let mut p = chain(2);
        match variant {
            0 => p.functions[1].code.insert(0, Op::Imm { dst: 3, value: 0 }),
            1 => p.functions[1].code.insert(
                0,
                Op::Assert {
                    value: 3,
                    expected: true,
                    message: "must execute".into(),
                },
            ),
            2 => p.functions[1].code[0] = Op::Local { dst: 0, offset: 8 },
            3 => {
                p.functions[1]
                    .code
                    .insert(1, Op::Local { dst: 0, offset: 0 });
            }
            4 => p.functions[1].code[1] = Op::Local { dst: 1, offset: 8 },
            5 => {
                p.functions[1].args[0].offset = 0;
                p.functions[1].code[0] = Op::Local { dst: 0, offset: 0 };
            }
            6 => p.functions[2].args[0].size = 4,
            7 => p.functions[2].result.size = 16,
            _ => unreachable!(),
        }
        let before = bincode::serialize(&p).unwrap();
        assert_eq!(
            eliminate_direct_forwarders(&mut p)
                .unwrap()
                .retargeted_calls,
            0,
            "variant {variant}"
        );
        assert_eq!(bincode::serialize(&p).unwrap(), before);
        if variant == 1 {
            for engine in engines() {
                assert!(
                    execute_with_engine(&p, &[7], Limits::default(), engine)
                        .unwrap_err()
                        .contains("must execute")
                );
            }
        }
    }
    let mut p = chain(2);
    for f in &mut p.functions {
        f.args.push(Slot {
            offset: 24,
            size: 8,
        });
    }
    for f in &mut p.functions[..2] {
        f.code.insert(0, Op::Local { dst: 2, offset: 24 });
        if let Op::Call { args, .. } = &mut f.code[3] {
            args.push(2);
        }
    }
    if let Op::Call { args, .. } = &mut p.functions[1].code[3] {
        args.reverse();
    }
    assert_eq!(
        eliminate_direct_forwarders(&mut p)
            .unwrap()
            .retargeted_calls,
        0
    );
    // Even correctly addressed arguments must not overlap each other.
    p.functions[1].args[1].offset = 16;
    if let Op::Call { args, .. } = &mut p.functions[1].code[3] {
        *args = vec![0, 0];
    }
    assert_eq!(
        eliminate_direct_forwarders(&mut p)
            .unwrap()
            .retargeted_calls,
        0
    );
}

#[test]
fn function_handles_and_entry_ids_stay_stable_and_callee_faults_still_fail() {
    let mut p = chain(3);
    p.functions[0].code.insert(
        0,
        Op::Imm {
            dst: 3,
            value: (FUNCTION_POINTER_TAG | 2) as u128,
        },
    );
    p.functions[0].code[3] = Op::CallIndirect {
        callee: 3,
        args: vec![0],
        arg_sizes: vec![8],
        destination: 1,
        result_size: 8,
    };
    let original = p.clone();
    assert_eq!(
        eliminate_direct_forwarders(&mut p)
            .unwrap()
            .retargeted_calls,
        1
    );
    unchanged_layouts(&original, &p);
    assert_eq!(
        bincode::serialize(&p.functions[0].code).unwrap(),
        bincode::serialize(&original.functions[0].code).unwrap()
    );
    for engine in engines() {
        assert_eq!(
            execute_with_engine(&p, &[7], Limits::default(), engine)
                .unwrap()
                .value,
            7 ^ 79
        );
    }
    p.entry = 1;
    let mut original = original;
    original.entry = 1;
    for engine in engines() {
        assert_eq!(
            execute_with_engine(&p, &[7], Limits::default(), engine)
                .unwrap()
                .value,
            execute_with_engine(&original, &[7], Limits::default(), engine)
                .unwrap()
                .value
        );
    }
    p.functions[3].code = vec![Op::Trap {
        message: "callee failure".into(),
    }];
    for engine in engines() {
        assert!(
            execute_with_engine(&p, &[7], Limits::default(), engine)
                .unwrap_err()
                .contains("callee failure")
        );
    }
}

#[test]
fn cycles_remain_recursive_and_long_chains_resolve_iteratively_and_idempotently() {
    for target in [0, 1] {
        let mut p = chain(2);
        if let Op::Call { function, .. } = &mut p.functions[1].code[2] {
            *function = target;
        }
        let before = bincode::serialize(&p).unwrap();
        assert_eq!(
            eliminate_direct_forwarders(&mut p)
                .unwrap()
                .retargeted_calls,
            0
        );
        assert_eq!(bincode::serialize(&p).unwrap(), before);
        for engine in engines() {
            assert!(
                execute_with_engine(
                    &p,
                    &[7],
                    Limits {
                        frames: 8,
                        ..Limits::default()
                    },
                    engine
                )
                .unwrap_err()
                .contains("call-depth limit")
            );
        }
    }
    let mut p = chain(10_000);
    let before = p.clone();
    let report = eliminate_direct_forwarders(&mut p).unwrap();
    assert_eq!(report.longest_chain, 10_000);
    assert_eq!(report.retargeted_calls, 9_999);
    unchanged_layouts(&before, &p);
    let once = bincode::serialize(&p).unwrap();
    assert_eq!(
        eliminate_direct_forwarders(&mut p)
            .unwrap()
            .retargeted_calls,
        0
    );
    assert_eq!(bincode::serialize(&p).unwrap(), once);
}

#[test]
fn invalid_programs_fail_validation_before_any_mutation() {
    for variant in 0..4 {
        let mut p = chain(2);
        match variant {
            0 => {
                p.functions[0].code[2] = Op::Call {
                    function: 99,
                    args: vec![0],
                    destination: 1,
                }
            }
            1 => {
                p.functions[0].code[0] = Op::Local {
                    dst: 99,
                    offset: 16,
                }
            }
            2 => p.functions[0].args[0].offset = usize::MAX,
            3 => p.version += 1,
            _ => unreachable!(),
        }
        let before = bincode::serialize(&p).unwrap();
        assert!(eliminate_direct_forwarders(&mut p).is_err());
        assert_eq!(bincode::serialize(&p).unwrap(), before);
    }
}

fn inline_options() -> LeafInlineOptions {
    LeafInlineOptions {
        program_growth_percent: 100,
        ..Default::default()
    }
}

#[test]
fn forwarding_before_expansion_removes_the_whole_chain_with_aliased_results() {
    for alias in [false, true] {
        let mut original = chain(3);
        if alias {
            original.functions[0].code[2] = Op::Call {
                function: 1,
                args: vec![0],
                destination: 0,
            };
            original.functions[0].code.insert(
                3,
                Op::Copy {
                    dst: 1,
                    src: 0,
                    size: 8,
                },
            );
        }
        let (mut old_order, _) = inline_leaves(&original, inline_options()).unwrap();
        eliminate_direct_forwarders(&mut old_order).unwrap();
        let (optimized, report) = optimize_calls(original.clone(), Some(inline_options())).unwrap();
        assert_eq!(report.forwarding_before_inline.unwrap().retargeted_calls, 2);
        assert!(
            !optimized.functions[0]
                .code
                .iter()
                .any(|op| matches!(op, Op::Call { .. }))
        );
        assert_eq!(optimized.functions.len(), original.functions.len());
        for engine in engines() {
            for seed in [0, 7, 255, 1 << 63, u64::MAX as u128] {
                let expected = execute_with_engine(&original, &[seed], Limits::default(), engine)
                    .unwrap()
                    .value;
                assert_eq!(
                    execute_with_engine(
                        &optimized,
                        &[seed],
                        Limits {
                            frames: 1,
                            ..Limits::default()
                        },
                        engine
                    )
                    .unwrap()
                    .value,
                    expected
                );
                assert!(
                    execute_with_engine(
                        &old_order,
                        &[seed],
                        Limits {
                            frames: 1,
                            ..Limits::default()
                        },
                        engine
                    )
                    .unwrap_err()
                    .contains("call-depth limit")
                );
            }
        }
    }
}

#[test]
fn composed_passes_preserve_indirect_handles_and_inlined_fault_origins() {
    let mut original = chain(3);
    // Handles encode ID + 1, reserving zero as invalid.
    original.functions[0].code.insert(
        0,
        Op::Imm {
            dst: 3,
            value: (FUNCTION_POINTER_TAG | 2) as u128,
        },
    );
    original.functions[0].code[3] = Op::CallIndirect {
        callee: 3,
        args: vec![0],
        arg_sizes: vec![8],
        destination: 1,
        result_size: 8,
    };
    original.functions[3].code.insert(
        2,
        Op::Assert {
            value: 0,
            expected: true,
            message: "leaf assertion".into(),
        },
    );
    let (optimized, report) = optimize_calls(original.clone(), Some(inline_options())).unwrap();
    assert!(report.inlining.unwrap()["selected_sites"].as_u64().unwrap() > 0);
    assert_eq!(
        bincode::serialize(&optimized.functions[0]).unwrap(),
        bincode::serialize(&original.functions[0]).unwrap()
    );
    for (id, function) in optimized.functions.iter().enumerate() {
        assert_eq!(function.name, original.functions[id].name);
        assert_eq!(
            bincode::serialize(&function.args).unwrap(),
            bincode::serialize(&original.functions[id].args).unwrap()
        );
        assert_eq!(
            bincode::serialize(&function.result).unwrap(),
            bincode::serialize(&original.functions[id].result).unwrap()
        );
    }
    for engine in engines() {
        for entry in [0, 1] {
            let mut p = optimized.clone();
            p.entry = entry;
            assert_eq!(
                execute_with_engine(&p, &[7], Limits::default(), engine)
                    .unwrap()
                    .value,
                7 ^ 79
            );
            let error = execute_with_engine(&p, &[0], Limits::default(), engine).unwrap_err();
            assert!(
                error.contains("leaf assertion") && error.contains("function-3"),
                "{error}"
            );
        }
    }
}

#[test]
fn forwarding_exposes_leaves_without_bypassing_existing_inline_guards() {
    for variant in 0..5 {
        let mut p = chain(3);
        let mut options = inline_options();
        match variant {
            0 => p.functions[3].frame_size = 520,
            1 => options.leaf_operations = 6,
            2 => options.caller_growth = 0,
            3 => options.program_growth_percent = 0,
            4 => p.functions[3].code.insert(
                0,
                Op::Assert {
                    value: 3,
                    expected: false,
                    message: "fresh register zero".into(),
                },
            ),
            _ => unreachable!(),
        }
        let original = p.clone();
        let (q, report) = optimize_calls(p, Some(options)).unwrap();
        assert_eq!(
            report.inlining.unwrap()["selected_sites"],
            0,
            "variant {variant}"
        );
        assert_eq!(report.forwarding_before_inline.unwrap().retargeted_calls, 2);
        unchanged_layouts(&original, &q);
        assert!(matches!(
            q.functions[0].code[2],
            Op::Call { function: 3, .. }
        ));
        for engine in engines() {
            assert_eq!(
                execute_with_engine(
                    &q,
                    &[7],
                    Limits {
                        frames: 2,
                        ..Limits::default()
                    },
                    engine
                )
                .unwrap()
                .value,
                7 ^ 79
            );
        }
    }
}

#[test]
fn no_inline_mode_and_recursive_forwarding_keep_existing_behavior() {
    let p = chain(3);
    let mut expected = p.clone();
    eliminate_direct_forwarders(&mut expected).unwrap();
    let (q, report) = optimize_calls(p, None).unwrap();
    assert!(report.inlining.is_none() && report.forwarding_before_inline.is_none());
    assert_eq!(report.inline_time, std::time::Duration::ZERO);
    assert_eq!(
        bincode::serialize(&q).unwrap(),
        bincode::serialize(&expected).unwrap()
    );
    for target in [0, 1] {
        let mut p = chain(2);
        if let Op::Call { function, .. } = &mut p.functions[1].code[2] {
            *function = target;
        }
        let before = bincode::serialize(&p).unwrap();
        let (q, report) = optimize_calls(p, Some(inline_options())).unwrap();
        assert_eq!(report.inlining.unwrap()["selected_sites"], 0);
        assert_eq!(bincode::serialize(&q).unwrap(), before);
        for engine in engines() {
            assert!(
                execute_with_engine(
                    &q,
                    &[7],
                    Limits {
                        frames: 8,
                        ..Limits::default()
                    },
                    engine
                )
                .unwrap_err()
                .contains("call-depth limit")
            );
        }
    }
}
