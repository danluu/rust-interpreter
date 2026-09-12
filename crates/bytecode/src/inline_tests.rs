use crate::{Binary, Function, Op, Program, Slot, VERSION, inline};
use crate::{Engine, Limits, execute_profiled, execute_with_engine};

fn options() -> inline::Options {
    inline::Options {
        program_growth_percent: 100,
        ..Default::default()
    }
}

// Run the owned result through the existing semantic fixtures, while checking
// exact output and diagnostics against the borrowed API on every input.
fn checked_transform(p: &Program, options: inline::Options) -> Result<(Program, serde_json::Value), String> {
    let borrowed = inline::transform(p, options);
    let owned = inline::transform_owned(p.clone(), options);
    match (&borrowed, &owned) {
        (Ok((before, report)), Ok((after, actual))) => {
            assert_eq!(bincode::serialize(before).unwrap(), bincode::serialize(after).unwrap());
            assert_eq!(report, actual);
        }
        (Err(before), Err(after)) => assert_eq!(before, after),
        _ => panic!("borrowed and owned inlining disagree: {borrowed:?}, {owned:?}"),
    }
    owned
}

#[test]
fn diagnostics_and_options_are_bounded() {
    let f = leaf(
        "large-diagnostic",
        0,
        0,
        vec![],
        Slot { offset: 0, size: 0 },
        vec![
            Op::Return,
            Op::Trap {
                message: "x".repeat(1024 * 1024),
            },
        ],
    );
    let p = root(f, &[], 0);
    let (_, report) = checked_transform(&p, options()).unwrap();
    assert_eq!(report["selected_sites"], 0);
    for opts in [
        inline::Options {
            caller_growth: 4097,
            ..options()
        },
        inline::Options {
            leaf_operations: 193,
            ..options()
        },
        inline::Options {
            program_growth_percent: 101,
            ..options()
        },
    ] {
        assert!(
            checked_transform(&p, opts)
                .unwrap_err()
                .contains("bounded limits")
        );
    }
}

#[test]
fn expansion_cannot_introduce_whole_caller_register_clearing() {
    let f = leaf(
        "branch",
        16,
        1,
        vec![],
        Slot { offset: 0, size: 0 },
        vec![
            Op::Imm { dst: 0, value: 1 },
            Op::Switch {
                value: 0,
                cases: vec![(1, 2)],
                otherwise: 3,
            },
            Op::Return,
            Op::Return,
        ],
    );
    let mut p = root(f, &[], 0);
    p.functions[0].code.insert(0, Op::Imm { dst: 3, value: 43 });
    p.functions[0].code.insert(
        3,
        Op::Store {
            address: 0,
            src: 3,
            size: 8,
        },
    );
    assert!(!crate::registers::needs_initial_zeroes_for_inlining(&p.functions[0]));
    let (q, report) = checked_transform(&p, options()).unwrap();
    assert_eq!(report["selected_sites"], 0);
    assert_eq!(format!("{p:?}"), format!("{q:?}"));
}
fn root(leaf: Function, argument_sizes: &[usize], result_offset: usize) -> Program {
    let args: Vec<_> = argument_sizes
        .iter()
        .enumerate()
        .map(|(i, size)| Slot {
            offset: i * 16,
            size: *size,
        })
        .collect();
    let mut code: Vec<_> = args
        .iter()
        .enumerate()
        .map(|(i, s)| Op::Local {
            dst: i as u32,
            offset: s.offset,
        })
        .collect();
    let destination = args.len() as u32;
    code.extend([
        Op::Local {
            dst: destination,
            offset: result_offset,
        },
        Op::Call {
            function: 1,
            args: (0..destination).collect(),
            destination,
        },
    ]);
    // Give the synthetic caller enough original code for the bounded 100%
    // growth policy; these writes affect only an otherwise unused register.
    code.extend((0..8).map(|_| Op::Imm { dst: 3, value: 0 }));
    code.push(Op::Return);
    let result = Slot {
        offset: result_offset,
        size: leaf.result.size,
    };
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![
            Function {
                name: "caller".into(),
                frame_size: 64,
                frame_align: 16,
                registers: 4,
                args,
                result,
                code,
            },
            leaf,
        ],
    }
}
fn leaf(
    name: &str,
    frame: usize,
    regs: usize,
    args: Vec<Slot>,
    result: Slot,
    code: Vec<Op>,
) -> Function {
    Function {
        name: name.into(),
        frame_size: frame,
        frame_align: 16,
        registers: regs,
        args,
        result,
        code,
    }
}
fn equivalent(p: &Program, args: &[u128], expected: u128) -> Program {
    let (q, stats) = checked_transform(p, options()).unwrap();
    assert!(stats["selected_sites"].as_u64().unwrap() > 0);
    assert_eq!(q.functions.len(), p.functions.len());
    assert_eq!(
        format!("{:?}", q.functions[1]),
        format!("{:?}", p.functions[1])
    );
    let reference = execute_with_engine(&q, args, Limits::default(), Engine::Interpreter).unwrap();
    assert_eq!(reference.value, expected);
    for engine in [Engine::Interpreter, Engine::Jit] {
        assert_eq!(
            execute_with_engine(p, args, Limits::default(), engine)
                .unwrap()
                .value,
            expected
        );
        let new = execute_with_engine(&q, args, Limits::default(), engine).unwrap();
        assert_eq!(new.value, expected);
        assert_eq!(new.instructions, reference.instructions);
        assert_eq!(new.peak_memory, reference.peak_memory);
        let (profiled, _) = execute_profiled(&q, args, Limits::default(), engine).unwrap();
        assert_eq!(profiled.value, expected);
        assert_eq!(profiled.instructions, new.instructions);
        let exact = Limits {
            instructions: new.instructions,
            ..Limits::default()
        };
        assert_eq!(
            execute_with_engine(&q, args, exact, engine).unwrap().value,
            expected
        );
        let short = Limits {
            instructions: new.instructions - 1,
            ..Limits::default()
        };
        assert!(
            execute_with_engine(&q, args, short, engine)
                .unwrap_err()
                .contains("instruction limit")
        );
    }
    q
}

#[test]
fn argument_overlap_order_and_result_alias_are_preserved() {
    let f = leaf(
        "overlap",
        16,
        2,
        vec![Slot { offset: 0, size: 8 }, Slot { offset: 4, size: 8 }],
        Slot {
            offset: 0,
            size: 16,
        },
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 16,
            },
            Op::Store {
                address: 0,
                src: 1,
                size: 16,
            },
            Op::Return,
        ],
    );
    let a = 0x8877665544332211u128;
    let b = 0xffeeddccbbaa0099u128;
    let expected = (a & 0xffff_ffff) | (b << 32);
    for destination in [0, 32] {
        equivalent(&root(f.clone(), &[8, 8], destination), &[a, b], expected);
    }
}

#[test]
fn each_invocation_resets_inline_frame_inside_a_caller_loop() {
    let f = leaf(
        "fresh-slot",
        16,
        4,
        vec![],
        Slot { offset: 8, size: 8 },
        vec![
            Op::Local { dst: 0, offset: 8 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
            Op::Imm { dst: 2, value: 1 },
            Op::Binary {
                dst: 1,
                overflow: 3,
                op: Binary::Add,
                a: 1,
                b: 2,
                bits: 64,
                signed: false,
            },
            Op::Store {
                address: 0,
                src: 1,
                size: 8,
            },
            Op::Return,
        ],
    );
    let mut p = root(f, &[], 8);
    p.functions[0].registers = 5;
    p.functions[0].code = vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Imm { dst: 1, value: 4 },
        Op::Store {
            address: 0,
            src: 1,
            size: 8,
        },
        Op::Local { dst: 2, offset: 8 },
        Op::Call {
            function: 1,
            args: vec![],
            destination: 2,
        },
        Op::Local { dst: 0, offset: 0 },
        Op::Load {
            dst: 1,
            address: 0,
            size: 8,
        },
        Op::Imm { dst: 3, value: 1 },
        Op::Binary {
            dst: 1,
            overflow: 4,
            op: Binary::Sub,
            a: 1,
            b: 3,
            bits: 64,
            signed: false,
        },
        Op::Store {
            address: 0,
            src: 1,
            size: 8,
        },
        Op::Switch {
            value: 1,
            cases: vec![(0, 11)],
            otherwise: 3,
        },
        Op::Return,
    ];
    equivalent(&p, &[], 1);
}

#[test]
fn internal_leaf_backedges_do_not_repeat_initialization() {
    let f = leaf(
        "internal-loop",
        16,
        7,
        vec![Slot { offset: 0, size: 8 }],
        Slot { offset: 8, size: 8 },
        vec![
            Op::Local { dst: 0, offset: 8 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
            Op::Imm { dst: 2, value: 1 },
            Op::Binary {
                dst: 1,
                overflow: 6,
                op: Binary::Add,
                a: 1,
                b: 2,
                bits: 64,
                signed: false,
            },
            Op::Store {
                address: 0,
                src: 1,
                size: 8,
            },
            Op::Local { dst: 3, offset: 0 },
            Op::Load {
                dst: 4,
                address: 3,
                size: 8,
            },
            Op::Binary {
                dst: 5,
                overflow: 6,
                op: Binary::Ge,
                a: 1,
                b: 4,
                bits: 64,
                signed: false,
            },
            Op::Switch {
                value: 5,
                cases: vec![(0, 0)],
                otherwise: 9,
            },
            Op::Return,
        ],
    );
    for n in [1, 3, 9] {
        equivalent(&root(f.clone(), &[8], 32), &[n], n);
    }
}

#[test]
fn wide_aliases_and_checked_overflow_destinations_are_relocated() {
    let alternate = (1u128 << 117) | 99;
    let f = leaf(
        "wide-select",
        16,
        3,
        vec![Slot {
            offset: 0,
            size: 16,
        }],
        Slot {
            offset: 0,
            size: 16,
        },
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 16,
            },
            Op::Imm {
                dst: 2,
                value: alternate,
            },
            Op::Select {
                dst: 1,
                condition: 1,
                yes: 1,
                no: 2,
            },
            Op::Store {
                address: 0,
                src: 1,
                size: 16,
            },
            Op::Return,
        ],
    );
    for value in [0, 1, 1u128 << 100, u128::MAX] {
        equivalent(
            &root(f.clone(), &[16], 0),
            &[value],
            if value == 0 { alternate } else { value },
        );
    }
    let f = leaf(
        "overflow-alias",
        16,
        3,
        vec![Slot {
            offset: 0,
            size: 16,
        }],
        Slot {
            offset: 0,
            size: 16,
        },
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 16,
            },
            Op::Cast {
                dst: 1,
                src: 1,
                from: 128,
                to: 64,
                signed: false,
            },
            Op::Imm { dst: 2, value: 1 },
            Op::Binary {
                dst: 1,
                overflow: 1,
                op: Binary::Add,
                a: 1,
                b: 2,
                bits: 64,
                signed: true,
            },
            Op::Store {
                address: 0,
                src: 1,
                size: 16,
            },
            Op::Return,
        ],
    );
    equivalent(&root(f, &[16], 32), &[i64::MAX as u128], 1);
}

#[test]
fn branch_returns_and_cold_failures_keep_original_diagnostic_identity() {
    let f = leaf(
        "branch-leaf",
        16,
        2,
        vec![Slot { offset: 0, size: 8 }],
        Slot { offset: 8, size: 8 },
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
            Op::Switch {
                value: 1,
                cases: vec![(0, 3), (0, 5), (2, 5)],
                otherwise: 4,
            },
            Op::Return,
            Op::Return,
            Op::Trap {
                message: "bad leaf".into(),
            },
        ],
    );
    let p = root(f, &[8], 32);
    equivalent(&p, &[0], 0);
    equivalent(&p, &[1], 0);
    let (q, stats) = checked_transform(&p, options()).unwrap();
    assert_eq!(stats["selected_sites"], 1);
    for engine in [Engine::Interpreter, Engine::Jit] {
        let old = execute_with_engine(&p, &[2], Limits::default(), engine).unwrap_err();
        let new = execute_with_engine(&q, &[2], Limits::default(), engine).unwrap_err();
        assert!(old.contains("bad leaf") && old.contains("branch-leaf"));
        assert!(new.contains("bad leaf") && new.contains("inlined from branch-leaf"));
    }
    let mut p = p;
    p.functions[1].code = vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load {
            dst: 1,
            address: 0,
            size: 8,
        },
        Op::Assert {
            value: 1,
            expected: true,
            message: "leaf condition".into(),
        },
        Op::Return,
    ];
    let (q, _) = checked_transform(&p, options()).unwrap();
    for engine in [Engine::Interpreter, Engine::Jit] {
        let e = execute_with_engine(&q, &[0], Limits::default(), engine).unwrap_err();
        assert!(e.contains("leaf condition") && e.contains("inlined from branch-leaf"));
    }
}

#[test]
fn unproven_storage_initial_values_alignment_and_growth_are_excluded() {
    let f = leaf(
        "identity",
        16,
        2,
        vec![Slot { offset: 0, size: 8 }],
        Slot { offset: 0, size: 8 },
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
            Op::Return,
        ],
    );
    let original = root(f, &[8], 32);
    for variant in 0..6 {
        let mut p = original.clone();
        let mut opts = options();
        match variant {
            0 => {
                p.functions[1].code = vec![
                    Op::Local { dst: 0, offset: 0 },
                    Op::Store {
                        address: 0,
                        src: 1,
                        size: 8,
                    },
                    Op::Return,
                ]
            }
            1 => p.functions[0].code[0] = Op::Imm { dst: 0, value: 16 },
            2 => p.functions[0].code[1] = Op::Imm { dst: 1, value: 48 },
            3 => p.functions[0].frame_align = 8,
            4 => opts.caller_growth = 0,
            5 => p.functions[1].code.push(Op::Imm { dst: 1, value: 0 }),
            _ => unreachable!(),
        }
        let (q, s) = checked_transform(&p, opts).unwrap();
        assert_eq!(s["selected_sites"], 0, "variant {variant}");
        assert_eq!(format!("{q:?}"), format!("{p:?}"));
    }
    let mut bad = original;
    bad.functions[1].code[0] = Op::Jump { target: 99 };
    assert!(
        checked_transform(&bad, options())
            .unwrap_err()
            .contains("invalid branch")
    );
}

#[test]
fn zero_sized_parameters_and_results_keep_valid_dangling_locals() {
    let f = leaf(
        "zero-size",
        0,
        2,
        vec![Slot { offset: 0, size: 0 }],
        Slot { offset: 0, size: 0 },
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Imm { dst: 1, value: 0 },
            Op::Return,
        ],
    );
    equivalent(&root(f, &[0], 32), &[0], 0);
}

#[test]
fn stronger_caller_alignment_and_large_register_banks_work() {
    let mut f = leaf(
        "aligned-address",
        32,
        4,
        vec![],
        Slot { offset: 8, size: 8 },
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Imm { dst: 1, value: 31 },
            Op::Binary {
                dst: 2,
                overflow: 3,
                op: Binary::And,
                a: 0,
                b: 1,
                bits: 64,
                signed: false,
            },
            Op::Local { dst: 0, offset: 8 },
            Op::Store {
                address: 0,
                src: 2,
                size: 8,
            },
            Op::Return,
        ],
    );
    f.frame_align = 32;
    let mut p = root(f, &[], 32);
    p.functions[0].frame_align = 64;
    p.functions[0].frame_size = 65;
    p.functions[0].registers = 4000;
    let q = equivalent(&p, &[], 0);
    assert!(q.functions[0].registers > 4000);
    assert_eq!(q.functions[0].frame_align, 64);
}

#[test]
fn rematerialization_uses_latest_proven_argument_and_result_offsets() {
    let f = leaf(
        "local-redefinition",
        16,
        2,
        vec![Slot { offset: 0, size: 8 }],
        Slot { offset: 0, size: 8 },
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
            Op::Return,
        ],
    );
    let mut p = root(f, &[8], 32);
    p.functions[0].args.push(Slot {
        offset: 16,
        size: 8,
    });
    p.functions[0].result.offset = 48;
    let call = p.functions[0]
        .code
        .iter()
        .position(|op| matches!(op, Op::Call { .. }))
        .unwrap();
    p.functions[0].code.splice(
        call..call,
        [
            Op::Local { dst: 0, offset: 16 },
            Op::Local { dst: 1, offset: 48 },
        ],
    );
    equivalent(&p, &[17, 93], 93);
}

mod medium_copy_tests;
mod owned_tests;
