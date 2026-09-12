use super::*;
use rust_interp_bytecode::{Binary, Engine, Limits};
fn slot(offset: usize, size: usize) -> Slot {
    Slot { offset, size }
}
fn function(
    name: &str,
    args: Vec<Slot>,
    result: Slot,
    code: Vec<Op>,
    registers: usize,
) -> Function {
    Function {
        name: name.into(),
        frame_size: 128,
        frame_align: 16,
        registers,
        args,
        result,
        code,
    }
}
fn program(functions: Vec<Function>) -> Program {
    Program {
        version: 5,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        functions,
        data: vec![],
        statics: vec![],
        thread_locals: vec![],
    }
}
fn binding(id: usize, f: &Function, slots: Vec<Slot>, eligible: Vec<bool>) -> Binding {
    let arguments = f
        .args
        .iter()
        .map(|s| slots.iter().position(|t| same(*s, *t)))
        .collect();
    Binding {
        function: id,
        name: f.name.clone(),
        slots,
        eligible,
        arguments,
    }
}
fn modes() -> Vec<(Engine, bool, bool)> {
    let mut modes = vec![(Engine::Interpreter, false, false)];
    if cfg!(all(target_arch = "aarch64", target_os = "macos")) {
        for resumable in [false, true] {
            for persistent in [false, true] {
                modes.push((Engine::Jit, resumable, persistent));
            }
        }
    }
    modes
}
fn check(original: &Program, a: &Artifact, args: &[u128], want: u128) {
    assert_eq!(
        rust_interp_bytecode::execute(original, args, Limits::default())
            .unwrap()
            .value,
        want
    );
    let bytes = a.encode().unwrap();
    assert_eq!(Artifact::decode(&bytes).unwrap().encode().unwrap(), bytes);
    let expected = a.execute(args, Limits::default()).unwrap();
    assert_eq!(expected.value, want);
    for (engine, resumable, persistent) in modes() {
        let limits = || Limits {
            jit_resumable_calls: resumable,
            jit_persistent_registers: persistent,
            ..Limits::default()
        };
        let actual = a.execute_with_engine(args, limits(), engine).unwrap();
        assert_eq!(
            (actual.value, actual.instructions),
            (want, expected.instructions)
        );
        let (profiled, _) = a.execute_profiled(args, limits(), engine).unwrap();
        assert_eq!(
            (profiled.value, profiled.instructions),
            (want, expected.instructions)
        );
        for instructions in [
            0,
            expected.instructions - 1,
            expected.instructions,
            expected.instructions + 1,
        ] {
            let observed = a.execute_with_engine(
                args,
                Limits {
                    instructions,
                    ..limits()
                },
                engine,
            );
            if instructions < expected.instructions {
                assert_eq!(
                    observed.unwrap_err(),
                    "interpreter instruction limit exceeded"
                );
            } else {
                assert_eq!(observed.unwrap().value, want);
            }
        }
    }
}
fn identity(size: usize) -> Function {
    function(
        "identity",
        vec![slot(16, size)],
        slot(0, size),
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::Load {
                dst: 1,
                address: 0,
                size: size as u8,
            },
            Op::Local { dst: 2, offset: 0 },
            Op::Store {
                address: 2,
                src: 1,
                size: size as u8,
            },
            Op::Return,
        ],
        3,
    )
}

#[test]
fn compiler_formal_inputs_and_implicit_returns_survive_move_elimination() {
    for size in [1, 2, 4, 8, 16] {
        let f = identity(size);
        let b = binding(0, &f, vec![f.result, f.args[0]], vec![true, true]);
        let p = program(vec![f]);
        let (a, r) = apply(p.clone(), vec![b]).unwrap();
        assert_eq!(
            (r.slots, r.argument_registers, r.result_registers),
            (2, 1, 1)
        );
        assert_eq!(r.removed_moves, 1);
        assert!(
            !a.program.functions[0]
                .code
                .iter()
                .any(|op| matches!(op, Op::Imm { .. }))
        );
        let value = 0xfedcba98765432100123456789abcdefu128;
        let want = if size == 16 {
            value
        } else {
            value & ((1u128 << (size * 8)) - 1)
        };
        check(&p, &a, &[value], want);
    }
}

#[test]
fn compiler_direct_call_aliases_and_all_memory_register_bridges() {
    for caller in [false, true] {
        for callee in [false, true] {
            for result in [false, true] {
                let root = function(
                    "root",
                    vec![],
                    slot(0, 8),
                    vec![
                        Op::Local { dst: 0, offset: 16 },
                        Op::Imm {
                            dst: 1,
                            value: 0x12345678,
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
                        Op::Call {
                            function: 1,
                            args: vec![0],
                            destination: 0,
                        },
                        Op::Local { dst: 2, offset: 0 },
                        Op::Copy {
                            dst: 2,
                            src: 0,
                            size: 8,
                        },
                        Op::Return,
                    ],
                    3,
                );
                let child = identity(8);
                let bs = vec![
                    binding(
                        0,
                        &root,
                        vec![root.result, slot(16, 8)],
                        vec![result, caller],
                    ),
                    binding(
                        1,
                        &child,
                        vec![child.result, child.args[0]],
                        vec![result, callee],
                    ),
                ];
                let p = program(vec![root, child]);
                let (a, r) = apply(p.clone(), bs).unwrap();
                assert_eq!(r.value_calls, if caller { 2 } else { 0 });
                assert_eq!(r.value_arguments, r.value_calls);
                check(&p, &a, &[], 0x12345678);
                if cfg!(all(target_arch = "aarch64", target_os = "macos")) {
                    let e = a
                        .execute_with_engine(
                            &[],
                            Limits {
                                jit_resumable_calls: true,
                                jit_persistent_registers: true,
                                ..Limits::default()
                            },
                            Engine::Jit,
                        )
                        .unwrap();
                    assert!(e.jit_resumable_calls > 0);
                    assert!(e.jit_resumable_returns >= 2);
                }
            }
        }
    }
}

#[test]
fn compiler_recursive_calls_keep_parent_inputs_and_results() {
    let f = function(
        "recursive",
        vec![slot(16, 8)],
        slot(0, 8),
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
            Op::Switch {
                value: 1,
                cases: vec![(0, 17)],
                otherwise: 3,
            },
            Op::Local { dst: 2, offset: 16 },
            Op::Load {
                dst: 3,
                address: 2,
                size: 8,
            },
            Op::Imm { dst: 4, value: 1 },
            Op::Binary {
                dst: 5,
                overflow: 6,
                op: Binary::Sub,
                a: 3,
                b: 4,
                bits: 64,
                signed: false,
            },
            Op::Local { dst: 7, offset: 32 },
            Op::Store {
                address: 7,
                src: 5,
                size: 8,
            },
            Op::Local { dst: 8, offset: 0 },
            Op::Call {
                function: 0,
                args: vec![7],
                destination: 8,
            },
            Op::Load {
                dst: 9,
                address: 8,
                size: 8,
            },
            Op::Binary {
                dst: 10,
                overflow: 6,
                op: Binary::Add,
                a: 3,
                b: 9,
                bits: 64,
                signed: false,
            },
            Op::Store {
                address: 8,
                src: 10,
                size: 8,
            },
            Op::Return,
            Op::Trap {
                message: "unreachable".into(),
            },
            Op::Return,
            Op::Local { dst: 11, offset: 0 },
            Op::Imm { dst: 12, value: 0 },
            Op::Store {
                address: 11,
                src: 12,
                size: 8,
            },
            Op::Return,
        ],
        13,
    );
    let b = binding(0, &f, vec![f.result, f.args[0], slot(32, 8)], vec![true; 3]);
    let p = program(vec![f]);
    let (a, r) = apply(p.clone(), vec![b]).unwrap();
    assert_eq!((r.slots, r.value_calls), (3, 1));
    for n in [0, 1, 2, 7, 17] {
        check(&p, &a, &[n], n * (n + 1) / 2);
    }
}

#[test]
fn compiler_backedge_skips_only_private_initialization() {
    let f = function(
        "loop",
        vec![],
        slot(0, 8),
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
            Op::Imm { dst: 2, value: 1 },
            Op::Binary {
                dst: 3,
                overflow: 4,
                op: Binary::Add,
                a: 1,
                b: 2,
                bits: 64,
                signed: false,
            },
            Op::Store {
                address: 0,
                src: 3,
                size: 8,
            },
            Op::Imm { dst: 5, value: 10 },
            Op::Binary {
                dst: 6,
                overflow: 4,
                op: Binary::Lt,
                a: 3,
                b: 5,
                bits: 64,
                signed: false,
            },
            Op::Switch {
                value: 6,
                cases: vec![(1, 0)],
                otherwise: 8,
            },
            Op::Local { dst: 7, offset: 16 },
            Op::Local { dst: 8, offset: 0 },
            Op::Copy {
                dst: 8,
                src: 7,
                size: 8,
            },
            Op::Return,
        ],
        9,
    );
    let b = binding(0, &f, vec![f.result, slot(16, 8)], vec![true; 2]);
    let p = program(vec![f]);
    let (a, r) = apply(p.clone(), vec![b]).unwrap();
    assert_eq!(r.private_registers, 1);
    check(&p, &a, &[], 10);
}

#[test]
fn compiler_zero_initialized_results_and_private_storage() {
    let f = function(
        "zero",
        vec![],
        slot(0, 8),
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Local { dst: 1, offset: 16 },
            Op::Load {
                dst: 2,
                address: 0,
                size: 8,
            },
            Op::Load {
                dst: 3,
                address: 1,
                size: 8,
            },
            Op::Binary {
                dst: 4,
                overflow: 5,
                op: Binary::Add,
                a: 2,
                b: 3,
                bits: 64,
                signed: false,
            },
            Op::Store {
                address: 0,
                src: 4,
                size: 8,
            },
            Op::Return,
        ],
        6,
    );
    let b = binding(0, &f, vec![f.result, slot(16, 8)], vec![true; 2]);
    let p = program(vec![f]);
    let (a, r) = apply(p.clone(), vec![b]).unwrap();
    assert_eq!((r.result_registers, r.private_registers), (1, 1));
    check(&p, &a, &[], 0);
}

#[test]
fn compiler_rejects_partial_indirect_escaped_and_nondominating_uses() {
    let prefixes = vec![
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 4,
            },
        ],
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::Store {
                address: 0,
                src: 0,
                size: 8,
            },
        ],
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::Call {
                function: 1,
                args: vec![0],
                destination: 1,
            },
        ],
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::CallIndirect {
                callee: 2,
                args: vec![0],
                arg_sizes: vec![8],
                destination: 1,
                result_size: 8,
            },
        ],
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::RegisterTlsDestructor {
                callback: 1,
                argument: 0,
            },
        ],
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::Jump { target: 2 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
        ],
        vec![
            Op::Jump { target: 2 },
            Op::Local { dst: 0, offset: 16 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
        ],
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::Imm { dst: 0, value: 0 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
        ],
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::CopyDynamic {
                dst: 1,
                src: 0,
                size: 2,
            },
        ],
    ];
    for mut code in prefixes {
        code.push(Op::Return);
        let f = function("reject", vec![], slot(0, 8), code, 3);
        let b = binding(0, &f, vec![f.result, slot(16, 8)], vec![false, true]);
        let p = program(vec![f, identity(4)]);
        let (a, r) = apply(p.clone(), vec![b]).unwrap();
        assert_eq!(r.slots, 0);
        assert_eq!(
            bincode::serialize(&a.program.functions).unwrap(),
            bincode::serialize(&p.functions).unwrap()
        );
    }
}

#[test]
fn compiler_rejects_interior_addresses_and_all_reused_local_definitions() {
    for reused in [false, true] {
        let f = function(
            "address",
            vec![],
            slot(0, 8),
            vec![
                Op::Local { dst: 0, offset: 16 },
                Op::Load {
                    dst: 1,
                    address: 0,
                    size: 8,
                },
                Op::Local { dst: 2, offset: 16 },
                Op::Load {
                    dst: 3,
                    address: 2,
                    size: 8,
                },
                Op::Local {
                    dst: if reused { 0 } else { 4 },
                    offset: if reused { 32 } else { 17 },
                },
                Op::Local { dst: 5, offset: 0 },
                Op::Store {
                    address: 5,
                    src: 3,
                    size: 8,
                },
                Op::Return,
            ],
            6,
        );
        let b = binding(
            0,
            &f,
            vec![f.result, slot(16, 8), slot(32, 8)],
            vec![false, true, true],
        );
        let (a, r) = apply(program(vec![f]), vec![b]).unwrap();
        assert_eq!(r.slots, 0);
        a.validate().unwrap();
    }
}

#[test]
fn compiler_rejects_colored_ineligible_and_overlapping_storage() {
    for slots in [
        vec![slot(0, 8), slot(16, 8), slot(16, 8)],
        vec![slot(0, 8), slot(16, 8), slot(20, 8)],
    ] {
        let f = identity(8);
        let b = binding(0, &f, slots, vec![false, true, false]);
        let (_, r) = apply(program(vec![f]), vec![b]).unwrap();
        assert_eq!(r.slots, 0);
    }
}

#[test]
fn compiler_checks_binding_identity_abi_and_extents() {
    for case in 0..6 {
        let f = identity(8);
        let mut b = binding(0, &f, vec![f.result, f.args[0]], vec![true; 2]);
        match case {
            0 => b.name.push('x'),
            1 => b.function = 1,
            2 => b.slots[0].offset = 64,
            3 => b.slots[1].offset = 64,
            4 => b.slots.push(slot(128, 1)),
            5 => b.arguments[0] = Some(9),
            _ => unreachable!(),
        }
        assert!(apply(program(vec![f]), vec![b]).is_err());
    }
    let f = identity(8);
    let bs = (0..2)
        .map(|_| binding(0, &f, vec![f.result, f.args[0]], vec![true; 2]))
        .collect();
    assert!(apply(program(vec![f]), bs).is_err());
}

#[test]
fn compiler_preserves_fault_classes_for_remaining_address_bridges() {
    for source in [false, true] {
        let f = function(
            "fault",
            vec![],
            slot(0, 8),
            vec![
                Op::Local { dst: 0, offset: 16 },
                Op::Imm {
                    dst: 1,
                    value: 1_000_000,
                },
                if source {
                    Op::Copy {
                        dst: 0,
                        src: 1,
                        size: 8,
                    }
                } else {
                    Op::Copy {
                        dst: 1,
                        src: 0,
                        size: 8,
                    }
                },
                Op::Return,
            ],
            2,
        );
        let b = binding(0, &f, vec![f.result, slot(16, 8)], vec![false, true]);
        let p = program(vec![f]);
        let (a, r) = apply(p.clone(), vec![b]).unwrap();
        assert_eq!(r.slots, 1);
        let expected = rust_interp_bytecode::execute(&p, &[], Limits::default()).unwrap_err();
        assert_eq!(a.execute(&[], Limits::default()).unwrap_err(), expected);
        for (engine, resumable, persistent) in modes() {
            let error = a
                .execute_with_engine(
                    &[],
                    Limits {
                        jit_resumable_calls: resumable,
                        jit_persistent_registers: persistent,
                        ..Limits::default()
                    },
                    engine,
                )
                .unwrap_err();
            assert!(
                error == expected
                    || (error == "JIT guest memory access failed"
                        && expected == "invalid guest memory access")
            );
        }
    }
}

#[test]
fn compiler_bounds_decline_before_mutation_and_legacy_partial_is_rejected() {
    for case in 0..3 {
        let mut f = identity(8);
        let mut b = binding(0, &f, vec![f.result, f.args[0]], vec![true; 2]);
        match case {
            0 => {
                b.slots.resize(MAX_LOCALS + 1, slot(32, 0));
                b.eligible.resize(MAX_LOCALS + 1, false);
            }
            1 => f.registers = MAX_REGISTERS + 1,
            2 => {
                f.code = vec![Op::Return; MAX_OPERATIONS + 1];
            }
            _ => unreachable!(),
        }
        let p = program(vec![f]);
        let (a, r) = apply(p.clone(), vec![b]).unwrap();
        assert_eq!(r.declined_functions, 1);
        assert_eq!(
            bincode::serialize(&p.functions).unwrap(),
            bincode::serialize(&a.program.functions).unwrap()
        );
    }
    let mut p = program(vec![identity(8)]);
    p.version = rust_interp_bytecode::VERSION | rust_interp_bytecode::PARTIAL_VALIDATION;
    assert!(apply(p, vec![]).unwrap_err().contains("strict"));
}

#[test]
fn compiler_last_local_target_remains_a_valid_faulting_operation() {
    let f = function(
        "last",
        vec![],
        slot(0, 8),
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 8,
            },
            Op::Jump { target: 3 },
            Op::Local { dst: 2, offset: 16 },
        ],
        3,
    );
    let b = binding(0, &f, vec![f.result, slot(16, 8)], vec![false, true]);
    let p = program(vec![f]);
    let (a, r) = apply(p.clone(), vec![b]).unwrap();
    assert_eq!(r.slots, 1);
    assert!(matches!(
        a.program.functions[0].code.last(),
        Some(Op::Local { .. })
    ));
    assert_eq!(
        a.execute(&[], Limits::default()).unwrap_err(),
        rust_interp_bytecode::execute(&p, &[], Limits::default()).unwrap_err()
    );
}
