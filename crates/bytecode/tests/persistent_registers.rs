#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{
    Binary, Engine, Function, Limits, Op, Program, Slot, VERSION, execute_profiled,
    execute_with_engine,
};
const WIDE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;

fn function(name: &str, code: Vec<Op>, registers: usize) -> Function {
    Function {
        name: name.into(),
        frame_size: 64,
        frame_align: 16,
        registers,
        args: vec![Slot {
            offset: 16,
            size: 16,
        }],
        result: Slot {
            offset: 0,
            size: 16,
        },
        code,
    }
}
fn program(call: bool, fallback: bool, far: bool) -> Program {
    let r = if far { 2050 } else { 0 };
    let mut code = vec![
        Op::Local { dst: r, offset: 0 },
        Op::Local {
            dst: r + 1,
            offset: 16,
        },
        Op::Load {
            dst: r + 2,
            address: r + 1,
            size: 16,
        },
        Op::Imm {
            dst: r + 3,
            value: 1,
        },
        Op::Imm {
            dst: r + 4,
            value: 3,
        },
        Op::Imm {
            dst: r + 6,
            value: 0,
        },
        Op::Jump { target: 7 },
    ];
    if call {
        code.push(Op::Call {
            function: 1,
            args: vec![r + 1],
            destination: r,
        });
    }
    code.extend([
        Op::Binary {
            dst: r + 2,
            overflow: r + 5,
            op: Binary::Sub,
            a: r + 2,
            b: r + 3,
            bits: 128,
            signed: false,
        },
        Op::Store {
            address: r,
            src: r + 2,
            size: 16,
        },
    ]);
    if fallback {
        code.push(Op::CopyDynamic {
            dst: r,
            src: r,
            size: r + 6,
        });
    }
    code.push(Op::Binary {
        dst: r + 4,
        overflow: r + 5,
        op: Binary::Sub,
        a: r + 4,
        b: r + 3,
        bits: 64,
        signed: false,
    });
    code.push(Op::Switch {
        value: r + 4,
        cases: vec![(0, code.len() + 1)],
        otherwise: 7,
    });
    code.push(Op::Return);
    let child = function(
        "native child",
        vec![
            Op::Local { dst: 0, offset: 16 },
            Op::Load {
                dst: 2,
                address: 0,
                size: 16,
            },
            Op::Local { dst: 0, offset: 0 },
            Op::Imm { dst: 3, value: 1 },
            Op::Imm { dst: 4, value: 2 },
            Op::Jump { target: 6 },
            Op::Binary {
                dst: 2,
                overflow: 5,
                op: Binary::Sub,
                a: 2,
                b: 3,
                bits: 128,
                signed: false,
            },
            Op::Binary {
                dst: 4,
                overflow: 5,
                op: Binary::Add,
                a: 4,
                b: 3,
                bits: 64,
                signed: false,
            },
            Op::Binary {
                dst: 3,
                overflow: 5,
                op: Binary::Sub,
                a: 3,
                b: 3,
                bits: 64,
                signed: false,
            },
            Op::Store {
                address: 0,
                src: 2,
                size: 16,
            },
            Op::Assert {
                value: 3,
                expected: false,
                message: "child zero".into(),
            },
            Op::Assert {
                value: 4,
                expected: true,
                message: "child counter".into(),
            },
            Op::Return,
        ],
        6,
    );
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![function("persistent loop", code, r as usize + 7), child],
    }
}

#[test]
fn full_width_loop_values_survive_native_and_vm_calls_and_every_budget_exit() {
    for call in [false, true] {
        for fallback in [false, true] {
            for far in [false, true] {
                let p = program(call, fallback, far);
                for input in [WIDE, 0, 1 << 127] {
                    let reference =
                        execute_with_engine(&p, &[input], Limits::default(), Engine::Interpreter)
                            .unwrap();
                    assert_eq!(reference.value, input.wrapping_sub(3));
                    for native in [false, true] {
                        for stubs in [false, true].into_iter().filter(|stubs| !*stubs || native) {
                            for budget in 0..=reference.instructions + 1 {
                                let config = || Limits {
                                    instructions: budget,
                                    jit_persistent_registers: true,
                                    jit_native_calls: native,
                                    jit_native_call_stubs: stubs,
                                    ..Limits::default()
                                };
                                let plain =
                                    execute_with_engine(&p, &[input], config(), Engine::Jit);
                                let observed =
                                    execute_profiled(&p, &[input], config(), Engine::Jit);
                                if budget < reference.instructions {
                                    assert_eq!(
                                        plain.unwrap_err(),
                                        "interpreter instruction limit exceeded"
                                    );
                                    assert_eq!(
                                        observed.unwrap_err(),
                                        "interpreter instruction limit exceeded"
                                    );
                                } else {
                                    let plain = plain.unwrap();
                                    let (got, profile) = observed.unwrap();
                                    for r in [&plain, &got] {
                                        assert_eq!(
                                            (r.value, r.instructions, r.peak_memory),
                                            (
                                                reference.value,
                                                reference.instructions,
                                                reference.peak_memory
                                            )
                                        );
                                        assert!(r.jit_register_functions > 0);
                                        assert!(r.jit_register_pairs >= 3);
                                        assert_eq!(r.jit_liveness_declines, 0);
                                    }
                                    let mut charged = 0;
                                    for f in profile.functions {
                                        charged += f.interpreted.iter().sum::<u64>();
                                        for (pc, hits) in f
                                            .jit_blocks
                                            .iter()
                                            .enumerate()
                                            .filter(|(_, n)| **n != 0)
                                        {
                                            charged += hits * (f.jit_block_ends[pc] - pc) as u64;
                                        }
                                        for (pc, hits) in f
                                            .jit_tree_blocks
                                            .iter()
                                            .enumerate()
                                            .filter(|(_, n)| **n != 0)
                                        {
                                            charged +=
                                                hits * (f.jit_tree_block_ends[pc] - pc) as u64;
                                        }
                                    }
                                    assert_eq!(charged, got.instructions);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn capacity_declines_and_an_interpreter_option_error_preserve_existing_behavior() {
    let p = program(true, true, false);
    for capacity in [0, 4, 64, 1024] {
        let r = execute_with_engine(
            &p,
            &[WIDE],
            Limits {
                jit_persistent_registers: true,
                jit_native_calls: true,
                jit_native_call_stubs: true,
                jit_code_bytes: capacity,
                ..Limits::default()
            },
            Engine::Jit,
        )
        .unwrap();
        assert_eq!(r.value, WIDE - 3);
        assert!(r.jit_bytes <= capacity);
    }
    let error = execute_with_engine(
        &p,
        &[WIDE],
        Limits {
            jit_persistent_registers: true,
            ..Limits::default()
        },
        Engine::Interpreter,
    )
    .unwrap_err();
    assert_eq!(error, "persistent registers require the JIT engine");
}
