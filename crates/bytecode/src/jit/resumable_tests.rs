use super::*;
use crate::{
    Engine, Execution, ExecutionProfile, Slot, VERSION, execute_profiled, execute_with_engine,
};

fn function(code: Vec<Op>) -> Function {
    Function {
        name: "resumable fixture".into(),
        frame_size: 32,
        frame_align: 16,
        registers: 8,
        args: vec![],
        result: Slot { offset: 0, size: 8 },
        code,
    }
}
fn program(functions: Vec<Function>) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        functions,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
    }
}
fn binary(dst: Reg, op: Binary, a: Reg, b: Reg) -> Op {
    Op::Binary {
        dst,
        overflow: 7,
        op,
        a,
        b,
        bits: 64,
        signed: false,
    }
}
fn looping_program(unsupported: bool) -> Program {
    let wide = (1u128 << 127) | 3;
    let root = function(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Imm {
            dst: 1,
            value: wide,
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
        Op::Imm {
            dst: 2,
            value: wide,
        },
        Op::Binary {
            dst: 3,
            overflow: 7,
            op: Binary::Eq,
            a: 1,
            b: 2,
            bits: 128,
            signed: false,
        },
        Op::Assert {
            value: 3,
            expected: true,
            message: "caller lost full-width value".into(),
        },
        Op::Return,
    ]);
    let mut child = function(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load {
            dst: 1,
            address: 0,
            size: 8,
        },
        Op::Imm { dst: 2, value: 5 },
        Op::Imm { dst: 3, value: 1 },
        Op::Local { dst: 4, offset: 8 },
        binary(1, Binary::Add, 1, 3),
        binary(2, Binary::Sub, 2, 3),
        Op::Switch {
            value: 2,
            cases: vec![(0, 8)],
            otherwise: 5,
        },
        Op::Store {
            address: 4,
            src: 1,
            size: 8,
        },
        Op::Return,
    ]);
    child.args = vec![Slot { offset: 0, size: 8 }];
    child.result = Slot { offset: 8, size: 8 };
    if unsupported {
        // A real interpreter-only operation in the descendant. Its result is
        // checked there before native Return may resume the parent's code.
        child.code.pop();
        child.code.extend([
            Op::Imm {
                dst: 5,
                value: (-3.0f64).to_bits() as u128,
            },
            Op::FloatUnary {
                dst: 5,
                op: crate::FloatUnary::Abs,
                src: 5,
                bits: 64,
            },
            Op::Imm {
                dst: 6,
                value: 3.0f64.to_bits() as u128,
            },
            binary(5, Binary::Eq, 5, 6),
            Op::Assert {
                value: 5,
                expected: true,
                message: "wrong descendant continuation".into(),
            },
            Op::Return,
        ]);
    }
    program(vec![root, child])
}
fn logical(profile: &ExecutionProfile) -> Vec<Vec<u64>> {
    profile
        .functions
        .iter()
        .map(|f| {
            let mut counts = f.interpreted.clone();
            for (blocks, ends) in [
                (&f.jit_blocks, &f.jit_block_ends),
                (&f.jit_tree_blocks, &f.jit_tree_block_ends),
            ] {
                for (pc, &hits) in blocks.iter().enumerate() {
                    if hits != 0 {
                        assert!(ends[pc] > pc && ends[pc] <= counts.len());
                        for count in &mut counts[pc..ends[pc]] {
                            *count += hits;
                        }
                    }
                }
            }
            counts
        })
        .collect()
}
fn equal_result(actual: Result<Execution, String>, expected: &Result<Execution, String>) {
    match (actual, expected) {
        (Ok(a), Ok(b)) => assert_eq!(
            (a.value, a.instructions, a.peak_memory),
            (b.value, b.instructions, b.peak_memory)
        ),
        (Err(a), Err(b)) => assert_eq!(a, *b),
        (a, b) => panic!("execution mismatch: {a:?} vs {b:?}"),
    }
}

#[test]
fn native_calls_loop_and_resume_through_descendant_vm_operations() {
    for unsupported in [false, true] {
        let p = looping_program(unsupported);
        let (reference, reference_profile) =
            execute_profiled(&p, &[], Limits::default(), Engine::Interpreter).unwrap();
        assert_eq!(reference.value, 10);
        assert!(trees::analyze(&p)[1].is_err());
        for persistent in [false, true] {
            let limits = || Limits {
                jit_resumable_calls: true,
                jit_persistent_registers: persistent,
                ..Limits::default()
            };
            let (actual, profile) = execute_profiled(&p, &[], limits(), Engine::Jit).unwrap();
            assert_eq!(
                (actual.value, actual.instructions, actual.peak_memory),
                (
                    reference.value,
                    reference.instructions,
                    reference.peak_memory
                )
            );
            assert!(actual.jit_resumable_calls >= 1);
            assert_eq!(actual.jit_resumable_returns, 2);
            assert_eq!(actual.jit_tree_calls, 0);
            assert_eq!(logical(&profile), logical(&reference_profile));
            assert_eq!(
                logical(&profile).iter().flatten().sum::<u64>(),
                actual.instructions
            );
            if unsupported {
                assert_eq!(profile.functions[1].interpreted[10], 2);
            }
            let unprofiled = execute_with_engine(&p, &[], limits(), Engine::Jit).unwrap();
            assert_eq!(
                (
                    unprofiled.value,
                    unprofiled.instructions,
                    unprofiled.peak_memory
                ),
                (
                    reference.value,
                    reference.instructions,
                    reference.peak_memory
                )
            );
        }
    }
}

#[test]
fn every_instruction_budget_and_code_capacity_preserves_vm_behavior() {
    let p = looping_program(true);
    let total = execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter)
        .unwrap()
        .instructions;
    for budget in 0..=total + 1 {
        let reference = execute_with_engine(
            &p,
            &[],
            Limits {
                instructions: budget,
                ..Limits::default()
            },
            Engine::Interpreter,
        );
        for capacity in [0, 256, MAX_CODE_BYTES] {
            for persistent in [false, true] {
                let limits = Limits {
                    instructions: budget,
                    jit_code_bytes: capacity,
                    jit_resumable_calls: true,
                    jit_persistent_registers: persistent,
                    ..Limits::default()
                };
                equal_result(
                    execute_with_engine(&p, &[], limits, Engine::Jit),
                    &reference,
                );
            }
        }
    }
}

#[test]
fn guest_depth_and_working_memory_limits_are_not_prepared_capacity() {
    let p = looping_program(false);
    for depth in 0..=3 {
        for bytes in [0, 16, 32, 100, 175, 176, 180, 300, 335, 336, 512] {
            let reference = execute_with_engine(
                &p,
                &[],
                Limits {
                    memory: bytes,
                    frames: depth,
                    ..Limits::default()
                },
                Engine::Interpreter,
            );
            for persistent in [false, true] {
                let limits = Limits {
                    memory: bytes,
                    frames: depth,
                    jit_resumable_calls: true,
                    jit_persistent_registers: persistent,
                    ..Limits::default()
                };
                equal_result(
                    execute_with_engine(&p, &[], limits, Engine::Jit),
                    &reference,
                );
            }
        }
    }
}

fn recursive_program(depth: usize) -> Program {
    let root = function(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Imm {
            dst: 1,
            value: depth as u128,
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
    ]);
    let mut child = function(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load {
            dst: 1,
            address: 0,
            size: 8,
        },
        Op::Local { dst: 2, offset: 8 },
        Op::Imm { dst: 3, value: 1 },
        Op::Switch {
            value: 1,
            cases: vec![(0, 12)],
            otherwise: 5,
        },
        binary(1, Binary::Sub, 1, 3),
        Op::Store {
            address: 0,
            src: 1,
            size: 8,
        },
        Op::Call {
            function: 1,
            args: vec![0],
            destination: 2,
        },
        Op::Load {
            dst: 1,
            address: 2,
            size: 8,
        },
        binary(1, Binary::Add, 1, 3),
        Op::Store {
            address: 2,
            src: 1,
            size: 8,
        },
        Op::Return,
        Op::Imm {
            dst: 5,
            value: (-3.0f64).to_bits() as u128,
        },
        Op::FloatUnary {
            dst: 5,
            op: crate::FloatUnary::Abs,
            src: 5,
            bits: 64,
        },
        Op::Imm {
            dst: 6,
            value: 3.0f64.to_bits() as u128,
        },
        binary(5, Binary::Eq, 5, 6),
        Op::Assert {
            value: 5,
            expected: true,
            message: "deepest VM fallback".into(),
        },
        Op::Store {
            address: 2,
            src: 1,
            size: 8,
        },
        Op::Return,
    ]);
    child.args = vec![Slot { offset: 0, size: 8 }];
    child.result = Slot { offset: 8, size: 8 };
    program(vec![root, child])
}

#[test]
fn recursive_native_calls_cross_preparation_boundaries_and_return_to_older_ancestors() {
    for depth in [0, 1, 63, 64, 65, 256, 1024] {
        let p = recursive_program(depth);
        let (reference, wanted_profile) =
            execute_profiled(&p, &[], Limits::default(), Engine::Interpreter).unwrap();
        assert_eq!(reference.value, depth as u128);
        for persistent in [false, true] {
            let limits = || Limits {
                jit_resumable_calls: true,
                jit_persistent_registers: persistent,
                ..Limits::default()
            };
            let (actual, profile) = execute_profiled(&p, &[], limits(), Engine::Jit).unwrap();
            assert_eq!(
                (actual.value, actual.instructions, actual.peak_memory),
                (
                    reference.value,
                    reference.instructions,
                    reference.peak_memory
                )
            );
            assert_eq!(logical(&profile), logical(&wanted_profile));
            assert_eq!(profile.functions[1].interpreted[13], 1);
            assert_eq!(actual.jit_resumable_returns, depth as u64 + 1);
            assert!(actual.jit_resumable_calls >= depth as u64 / 2);
            let actual = execute_with_engine(&p, &[], limits(), Engine::Jit).unwrap();
            assert_eq!(
                (actual.value, actual.instructions, actual.peak_memory),
                (
                    reference.value,
                    reference.instructions,
                    reference.peak_memory
                )
            );
        }
    }
    let p = recursive_program(70);
    for frames in [1, 2, 64, 65, 70, 71, 72] {
        let reference = execute_with_engine(
            &p,
            &[],
            Limits {
                frames,
                ..Limits::default()
            },
            Engine::Interpreter,
        );
        equal_result(
            execute_with_engine(
                &p,
                &[],
                Limits {
                    frames,
                    jit_resumable_calls: true,
                    jit_persistent_registers: true,
                    ..Limits::default()
                },
                Engine::Jit,
            ),
            &reference,
        );
    }
}

#[test]
fn fixed_native_host_frame_preserves_all_callee_saved_registers_on_every_exit() {
    for fault in ["none", "argument", "result", "assert", "unsupported"] {
        let mut p = looping_program(fault == "unsupported");
        if fault == "argument" {
            p.functions[0].code[0] = Op::Imm { dst: 0, value: 0 };
        }
        if fault == "result" {
            p.functions[0].code[2] = Op::Call {
                function: 1,
                args: vec![0],
                destination: 6,
            };
        }
        if fault == "assert" {
            p.functions[1].code[8] = Op::Assert {
                value: 2,
                expected: true,
                message: "expected native fault".into(),
            };
        }
        crate::validate(&p).unwrap();
        for persistent in [false, true] {
            for profiled in [false, true] {
                for prepared in [false, true] {
                    let mut jit =
                        Jit::new_resumable(&p, profiled, MAX_CODE_BYTES, persistent).unwrap();
                    jit.ensure_function(0).unwrap();
                    if prepared {
                        jit.ensure_function(1).unwrap();
                    }
                    for (frame_end, memory_end, register_end, working_budget) in [
                        (1, 256, 24, 1024),
                        (3, 256, 24, 1024),
                        (3, 48, 24, 1024),
                        (3, 256, 8, 1024),
                        (3, 256, 24, 200),
                    ] {
                        let storage_ready = frame_end > 1
                            && memory_end >= 80
                            && register_end >= 16
                            && working_budget >= 336;
                        for budget in 0..=60 {
                            let mut memory = vec![0u8; 288];
                            memory[48..256].fill(0xbd);
                            memory[256..].fill(0xad);
                            let mut registers = vec![0u128; 32];
                            registers[8..24].fill(0xee);
                            registers[24..].fill(u128::MAX - 7);
                            let root = Frame {
                                function: 0,
                                pc: 0,
                                base: 16,
                                register_base: 0,
                                return_address: 0,
                                tls_callback: false,
                            };
                            let canary = Frame {
                                function: 987,
                                pc: 456,
                                base: 123,
                                register_base: 789,
                                return_address: 321,
                                tls_callback: true,
                            };
                            let mut frames = [root, Frame::default(), Frame::default(), canary];
                            let mut hits: Vec<_> = p
                                .functions
                                .iter()
                                .map(|f| vec![0u64; f.code.len()])
                                .collect();
                            let profiles: Vec<_> =
                                hits.iter_mut().map(|row| row.as_mut_ptr()).collect();
                            let mut cursor = ResumeCursor {
                                state: State {
                                    remaining: budget,
                                    profile_hits: profiles[0],
                                    memory_len: 48,
                                    peak_linear: 48,
                                    register_len: 8,
                                    frame_len: 1,
                                    calls: 0,
                                    returns: 0,
                                },
                                frames: frames.as_mut_ptr(),
                                registers: registers.as_mut_ptr(),
                                entries: jit.resumable.as_ref().unwrap().pointers.as_ptr(),
                                profiles: profiles.as_ptr(),
                                memory_end,
                                register_end,
                                frame_end,
                                frame_limit: 3,
                                working_budget,
                            };
                            let args = [
                                registers.as_mut_ptr() as usize,
                                16,
                                memory.as_mut_ptr() as usize,
                                48,
                                16,
                                0,
                                0,
                                std::ptr::addr_of_mut!(cursor) as usize,
                            ];
                            // SAFETY: exclusive initialized/canary-backed storage, a
                            // validated program and entries emitted by this same JIT.
                            let output = unsafe {
                                jit.code
                                    .as_ref()
                                    .unwrap()
                                    .tree_abi_probe(jit.blocks[0][0].unwrap().offset, args)
                            };
                            assert_eq!(&output[1..5], &[0x1357, 0x2468, 0x3579, 0x468a]);
                            assert_eq!(
                                &output[7..],
                                &[0x579b, 0x68ac, 0x79bd, 0x8ace, 0x9bdf, 0xace0]
                            );
                            assert_eq!(output[5], output[6]);
                            assert_eq!(output[6] % 16, 0);
                            assert!(cursor.state.remaining <= budget);
                            assert!(cursor.state.frame_len <= frame_end);
                            assert_eq!(frames[3], canary);
                            assert!(memory[256..].iter().all(|&b| b == 0xad));
                            assert!(registers[24..].iter().all(|&r| r == u128::MAX - 7));
                            if profiled {
                                let mut count = 0;
                                for (f, row) in hits.iter().enumerate() {
                                    for (pc, &hits) in row.iter().enumerate() {
                                        if hits > 0 {
                                            count +=
                                                hits * (jit.blocks[f][pc].unwrap().end - pc) as u64;
                                        }
                                    }
                                }
                                assert_eq!(count, budget - cursor.state.remaining);
                            }
                            if !prepared || !storage_ready {
                                assert_eq!(
                                    (
                                        cursor.state.calls,
                                        cursor.state.returns,
                                        cursor.state.memory_len
                                    ),
                                    (0, 0, 48)
                                );
                                assert!(memory[48..256].iter().all(|&b| b == 0xbd));
                                assert!(registers[8..24].iter().all(|&r| r == 0xee));
                            }
                            if prepared && storage_ready && budget == 60 {
                                assert_eq!(
                                    output[0] as u64 >= FAILURE_MIN,
                                    ["argument", "result", "assert"].contains(&fault)
                                );
                                if fault == "none" {
                                    assert_eq!((cursor.state.calls, cursor.state.returns), (2, 2));
                                }
                                if fault == "unsupported" {
                                    assert_eq!((cursor.state.frame_len, frames[1].pc), (2, 10));
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
fn incompatible_runtime_options_are_rejected_before_execution() {
    let p = looping_program(false);
    assert_eq!(
        execute_with_engine(
            &p,
            &[],
            Limits {
                jit_resumable_calls: true,
                ..Limits::default()
            },
            Engine::Interpreter
        )
        .unwrap_err(),
        "resumable calls require the JIT engine"
    );
    for stubs in [false, true] {
        assert_eq!(
            execute_with_engine(
                &p,
                &[],
                Limits {
                    jit_resumable_calls: true,
                    jit_native_calls: true,
                    jit_native_call_stubs: stubs,
                    ..Limits::default()
                },
                Engine::Jit
            )
            .unwrap_err(),
            "resumable calls cannot be combined with native tree/stub calls"
        );
    }
}
