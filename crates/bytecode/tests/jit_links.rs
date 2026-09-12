#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{
    Binary, Engine, Function, Limits, Op, Program, Slot, Unary, VERSION, execute_profiled,
    execute_with_engine,
};

fn program(code: Vec<Op>, registers: usize, arguments: bool) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![Function {
            name: "linked".into(),
            frame_size: 64,
            frame_align: 16,
            registers,
            args: if arguments {
                vec![Slot {
                    offset: 0,
                    size: 16,
                }]
            } else {
                vec![]
            },
            result: Slot {
                offset: 16,
                size: 16,
            },
            code,
        }],
    }
}
fn check(p: &Program, args: &[u128], value: u128, steps: u64, entries: u64) {
    let limits = || Limits {
        instructions: steps,
        ..Limits::default()
    };
    let reference = execute_with_engine(p, args, limits(), Engine::Interpreter).unwrap();
    let ordinary = execute_with_engine(p, args, limits(), Engine::Jit).unwrap();
    let (observed, profile) = execute_profiled(p, args, limits(), Engine::Jit).unwrap();
    assert_eq!(reference.value, value);
    assert_eq!(reference.instructions, steps);
    for result in [&ordinary, &observed] {
        assert_eq!(result.value, value);
        assert_eq!(result.instructions, steps);
        assert_eq!(result.peak_memory, reference.peak_memory);
        assert_eq!(result.jit_entries, entries);
    }
    assert_eq!(ordinary.jit_instructions, observed.jit_instructions);
    let mut interpreted = 0;
    let mut compiled = 0;
    for f in &profile.functions {
        interpreted += f.interpreted.iter().sum::<u64>();
        for (pc, hits) in f.jit_blocks.iter().enumerate() {
            if *hits != 0 {
                compiled += hits * (f.jit_block_ends[pc] - pc) as u64;
            }
        }
    }
    assert_eq!(compiled, observed.jit_instructions);
    assert_eq!(interpreted + compiled, steps);
}
fn budget_error(p: &Program, args: &[u128], budget: u64, expected: &str) {
    let limits = || Limits {
        instructions: budget,
        ..Limits::default()
    };
    for engine in [Engine::Interpreter, Engine::Jit] {
        assert_eq!(
            execute_with_engine(p, args, limits(), engine).unwrap_err(),
            expected
        );
        assert_eq!(
            execute_profiled(p, args, limits(), engine).unwrap_err(),
            expected
        );
    }
}

#[test]
fn linked_backedges_and_exits_share_one_native_entry_and_exact_profiles() {
    for n in [1u128, 2, 7, 31, 10_000] {
        let p = program(
            vec![
                Op::Local { dst: 0, offset: 16 },
                Op::Imm { dst: 1, value: n },
                Op::Imm { dst: 2, value: 1 },
                Op::Imm { dst: 3, value: 0 },
                Op::Jump { target: 5 },
                Op::Binary {
                    dst: 3,
                    overflow: 4,
                    op: Binary::Add,
                    a: 3,
                    b: 1,
                    bits: 64,
                    signed: false,
                },
                Op::Binary {
                    dst: 1,
                    overflow: 4,
                    op: Binary::Sub,
                    a: 1,
                    b: 2,
                    bits: 64,
                    signed: false,
                },
                Op::Switch {
                    value: 1,
                    cases: vec![(0, 8)],
                    otherwise: 5,
                },
                Op::Store {
                    address: 0,
                    src: 3,
                    size: 16,
                },
                Op::Imm { dst: 5, value: 13 },
                Op::Imm { dst: 5, value: 17 },
                Op::Return,
            ],
            6,
            false,
        );
        let steps = 3 * n as u64 + 9;
        check(&p, &[], n * (n + 1) / 2, steps, 1);
        let (_, profile) = execute_profiled(&p, &[], Limits::default(), Engine::Jit).unwrap();
        assert_eq!(profile.functions[0].jit_blocks[0], 1);
        assert_eq!(profile.functions[0].jit_blocks[5], n as u64);
        assert_eq!(profile.functions[0].jit_blocks[8], 1);
        let budgets = if n < 100 {
            (0..steps).collect::<Vec<_>>()
        } else {
            vec![0, 1, 4, 5, 6, 7, steps - 2, steps - 1]
        };
        for budget in budgets {
            budget_error(&p, &[], budget, "interpreter instruction limit exceeded");
        }
    }
}

#[test]
fn mixed_short_and_unsupported_successors_return_to_the_vm() {
    let p = program(
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load {
                dst: 1,
                address: 0,
                size: 16,
            },
            Op::Switch {
                value: 1,
                cases: vec![(0, 3), (1u128 << 64, 5), (1u128 << 64, 3)],
                otherwise: 7,
            },
            Op::Imm { dst: 2, value: 7 },
            Op::Jump { target: 7 },
            Op::Imm { dst: 2, value: 11 },
            Op::Jump { target: 7 },
            Op::Imm { dst: 3, value: 5 },
            Op::Imm { dst: 4, value: 1 },
            Op::Unary {
                dst: 5,
                src: 1,
                bits: 128,
                op: Unary::CountOnes,
            },
            Op::Binary {
                dst: 2,
                overflow: 4,
                op: Binary::Add,
                a: 2,
                b: 5,
                bits: 64,
                signed: false,
            },
            Op::Local { dst: 0, offset: 16 },
            Op::Store {
                address: 0,
                src: 2,
                size: 16,
            },
            Op::Return,
        ],
        6,
        true,
    );
    for value in [0, 1u128 << 64, 1, u128::MAX] {
        let prefix = if value == 0 {
            7
        } else if value == 1u128 << 64 {
            11
        } else {
            0
        };
        let steps = if prefix == 0 { 10 } else { 12 };
        check(&p, &[value], prefix + value.count_ones() as u128, steps, 2);
        for budget in 0..steps {
            budget_error(
                &p,
                &[value],
                budget,
                "interpreter instruction limit exceeded",
            );
        }
    }
}

#[test]
fn fallthrough_links_cross_region_limits_with_large_register_addresses() {
    let mut code = vec![Op::Local { dst: 0, offset: 16 }];
    code.extend((0..3500).map(|value| Op::Imm { dst: 5000, value }));
    code.extend([
        Op::Store {
            address: 0,
            src: 5000,
            size: 16,
        },
        Op::Return,
    ]);
    let steps = code.len() as u64;
    let p = program(code, 5001, false);
    check(&p, &[], 3499, steps, 1);
    for budget in [
        0,
        1,
        1023,
        1024,
        1025,
        2047,
        2048,
        2049,
        3071,
        3072,
        3073,
        steps - 1,
    ] {
        budget_error(&p, &[], budget, "interpreter instruction limit exceeded");
    }
}

#[test]
fn faults_after_linked_blocks_keep_budget_precedence() {
    for (value, denominator, fault, message) in [
        (
            7,
            0,
            Op::Binary {
                dst: 4,
                overflow: 5,
                op: Binary::Div,
                a: 2,
                b: 3,
                bits: 64,
                signed: false,
            },
            "integer division by zero",
        ),
        (
            1u128 << 63,
            u64::MAX as u128,
            Op::Binary {
                dst: 4,
                overflow: 5,
                op: Binary::Div,
                a: 2,
                b: 3,
                bits: 64,
                signed: true,
            },
            "signed division overflow",
        ),
        (
            0,
            1,
            Op::Assert {
                value: 2,
                expected: true,
                message: "linked failure".into(),
            },
            "guest assertion: linked failure in linked",
        ),
    ] {
        let p = program(
            vec![
                Op::Imm { dst: 0, value: 0 },
                Op::Imm { dst: 1, value: 1 },
                Op::Jump { target: 3 },
                Op::Imm { dst: 2, value },
                Op::Imm {
                    dst: 3,
                    value: denominator,
                },
                Op::Jump { target: 6 },
                fault,
                Op::Local { dst: 0, offset: 16 },
                Op::Store {
                    address: 0,
                    src: 4,
                    size: 16,
                },
                Op::Return,
            ],
            6,
            false,
        );
        for budget in 0..=11 {
            budget_error(
                &p,
                &[],
                budget,
                if budget < 7 {
                    "interpreter instruction limit exceeded"
                } else {
                    message
                },
            );
        }
    }
}

#[test]
fn heap_pointers_survive_copy_scratch_registers_across_links() {
    let value = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;
    let p = program(
        vec![
            Op::Imm { dst: 0, value: 32 },
            Op::Imm { dst: 1, value: 16 },
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
            Op::Local { dst: 4, offset: 32 },
            Op::Copy {
                dst: 4,
                src: 2,
                size: 32,
            },
            Op::Jump { target: 8 },
            Op::Copy {
                dst: 2,
                src: 4,
                size: 32,
            },
            Op::Load {
                dst: 3,
                address: 2,
                size: 16,
            },
            Op::Imm { dst: 5, value: 0 },
            Op::Jump { target: 12 },
            Op::Local { dst: 4, offset: 16 },
            Op::Store {
                address: 4,
                src: 3,
                size: 16,
            },
            Op::Imm { dst: 5, value: 1 },
            Op::Deallocate {
                pointer: 2,
                size: 0,
                align: 1,
            },
            Op::Return,
        ],
        6,
        false,
    );
    check(&p, &[], value, 17, 1);
    for budget in 0..17 {
        budget_error(&p, &[], budget, "interpreter instruction limit exceeded");
    }
}

#[test]
fn falling_off_code_retains_budget_before_invalid_pc_ordering() {
    let p = program(
        vec![
            Op::Imm { dst: 0, value: 0 },
            Op::Imm { dst: 1, value: 1 },
            Op::Jump { target: 3 },
            Op::Imm { dst: 2, value: 2 },
            Op::Imm { dst: 3, value: 3 },
            Op::Imm { dst: 4, value: 4 },
        ],
        5,
        false,
    );
    for budget in 0..=7 {
        budget_error(
            &p,
            &[],
            budget,
            if budget <= 6 {
                "interpreter instruction limit exceeded"
            } else {
                "invalid bytecode PC"
            },
        );
    }
}
