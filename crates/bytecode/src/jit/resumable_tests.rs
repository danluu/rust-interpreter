use super::*;
use crate::{
    Engine, Execution, ExecutionProfile, Slot, VERSION, execute_profiled, execute_with_engine,
};

#[path = "resumable_tree_bridge_tests.rs"]
mod bridge_tests;

#[test]
fn fixed_zeroing_matches_every_dirty_extent_and_unaligned_start() {
    let mut code = platform::Code::reserve(32768).unwrap();
    let mut entries = vec![];
    for size in 0..=256 {
        let mut a = Assembler::default();
        a.mov(11, 2);
        a.zero_fixed(size);
        a.mov(0, 31);
        a.emit(0xd65f03c0);
        entries.push((size, code.append(&a.words).unwrap()));
    }
    let mut registers = [0u128; 1];
    for (size, entry) in entries {
        for alignment in 0..64 {
            let start = 64 + alignment;
            let mut actual = vec![0xa5; start + size + 64];
            let mut expected = actual.clone();
            expected[start..start + size].fill(0);
            // SAFETY: this emitter-owned leaf receives initialized, stable
            // backing for exactly the proven range. Other pointers are unused.
            let result = unsafe { code.call(entry, registers.as_mut_ptr(), 0,
                actual.as_mut_ptr().add(start), size, 0, std::ptr::null_mut(), 0, std::ptr::null_mut()) };
            assert_eq!(result, 0);
            assert_eq!(actual, expected, "size {size}, alignment {alignment}");
        }
    }
}

#[test]
fn call_frame_clear_matches_actual_padding_and_preserves_live_call_registers() {
    let mut code = platform::Code::reserve(128 * 1024).unwrap();
    let mut caller = function(vec![Op::Return]);
    caller.frame_align = 1;
    let mut entries = vec![];
    for size in [0usize, 1, 2, 7, 8, 15, 16, 17, 31, 32, 63, 64, 127, 128, 129, 255, 256, 257, 513] {
        let mut callee = caller.clone();
        callee.frame_align = 4096;
        callee.frame_size = size;
        let mut a = Assembler::default();
        a.resumable_save_host(false);
        a.mov(21, 1); // test's exact prefix length, relative to the host slice
        a.mov(11, 2);
        a.three(0x8b000000, 12, 2, 3);
        a.imm(16, 0x1357);
        a.imm(17, 0x2468);
        a.imm(22, 0x3579);
        a.clear_call_frame(&caller, &callee).unwrap();
        for (register, offset) in [(16, 0), (17, 8), (22, 16)] {
            a.store64(register, 0, offset);
        }
        a.mov(0, 31);
        a.resumable_save_host(true);
        a.emit(0xd65f03c0);
        entries.push((size.max(1), code.append(&a.words).unwrap()));
    }
    for (size, entry) in entries {
        for padding in (0..=64).chain([127, 255, 4095]) {
            for offset in 0..16 {
                let start = 64 + offset;
                let len = padding + size;
                let mut actual = vec![0xa5; start + len + 64];
                let mut expected = actual.clone();
                expected[start..start + len].fill(0);
                let mut registers = [0u128; 2];
                // SAFETY: this owned leaf clears exactly the supplied live
                // slice; all backing remains initialized and stable. Prefix
                // and suffix canaries are compared without reading outside it.
                let result = unsafe { code.call(entry, registers.as_mut_ptr(), padding,
                    actual.as_mut_ptr().add(start), len, 0,
                    std::ptr::null_mut(), 0, std::ptr::null_mut()) };
                assert_eq!(result, 0);
                assert_eq!(actual, expected, "size {size}, padding {padding}, start {start}");
                assert_eq!(registers, [(0x2468u128 << 64) | 0x1357, 0x3579]);
            }
        }
    }
}

#[test]
fn fixed_clear_layout_requires_an_already_aligned_extent() {
    let mut caller = function(vec![Op::Return]);
    let mut callee = caller.clone();
    for caller_align in [1, 2, 4, 8, 16, 32, 64, 128, 256, 4096] {
        for callee_align in [1, 2, 4, 8, 16, 32, 64, 128, 256, 4096] {
            for caller_size in [0, 1, 7, 8, 15, 16, 17, 33, 153, 256, 257, 8192] {
                for callee_size in [0, 1, 7, 8, 15, 16, 17, 72, 153, 208, 255, 256, 257] {
                    caller.frame_align = caller_align; caller.frame_size = caller_size;
                    callee.frame_align = callee_align; callee.frame_size = callee_size;
                    let fixed = fixed_frame_clear_size(&caller, &callee);
                    if caller_align < callee_align || caller_size.max(1) % callee_align != 0 {
                        assert_eq!(fixed, None); continue;
                    }
                    // Independent layout oracle: seek the next aligned byte.
                    for base in [0, caller_align, caller_align * 7] {
                        let end = base + caller_size.max(1);
                        let next = (end..).find(|n| n % callee_align == 0).unwrap();
                        let expected = next - end + callee_size.max(1);
                        assert_eq!(fixed, (expected <= 256).then_some(expected));
                    }
                }
            }
        }
    }
}

#[test]
fn fixed_clear_proof_survives_retained_alignment_history() {
    // Arithmetic layout oracle only: each return can retain padding inserted
    // before an earlier callee. Every accepted fixed range must still match
    // the actual end after arbitrary sequences of those round-ups.
    let alignments = [1usize, 2, 4, 8, 16, 64, 256, 4096];
    let mut caller = function(vec![Op::Return]);
    let mut callee = caller.clone();
    for caller_align in alignments {
        for caller_size in [0usize, 1, 7, 16, 17, 32, 33, 256, 257] {
            caller.frame_align = caller_align;
            caller.frame_size = caller_size;
            for callee_align in alignments {
                callee.frame_align = callee_align;
                for callee_size in [0usize, 1, 17, 255, 256, 257] {
                    callee.frame_size = callee_size;
                    let Some(fixed) = fixed_frame_clear_size(&caller, &callee) else { continue; };
                    for first_align in alignments {
                        for second_align in alignments {
                            let mut end = caller_align * 3 + caller_size.max(1);
                            for alignment in [first_align, second_align] {
                                end = end.div_ceil(alignment) * alignment;
                            }
                            let next = end.div_ceil(callee_align) * callee_align;
                            assert_eq!(fixed, next - end + callee_size.max(1));
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn reused_guest_frames_clear_padding_and_preserve_limits() {
    for (caller_size, caller_align, callee_align) in [(33usize, 16usize, 16usize), (17, 16, 64), (0, 16, 16)] {
        for size in [0, 1, 7, 8, 15, 16, 17, 72, 153, 208, 255, 256, 257] {
            let mut caller = function(vec![Op::Local { dst: 0, offset: 0 }]);
            caller.frame_size = caller_size;
            caller.frame_align = caller_align;
            caller.result.size = 0;
            // Repeated calls ensure the saved backing is dirty and both
            // callees are ready for direct native transitions on the repeat.
            for id in [1, 2, 1, 2] {
                caller.code.push(Op::Call { function: id, args: vec![], destination: 0 });
            }
            caller.code.push(Op::Return);
            let mut dirty = function(vec![Op::Imm { dst: 1, value: u128::MAX }]);
            dirty.frame_size = 512; dirty.frame_align = 1; dirty.result.size = 0;
            for offset in (0..512).step_by(16) {
                dirty.code.push(Op::Local { dst: 0, offset });
                dirty.code.push(Op::Store { address: 0, src: 1, size: 16 });
            }
            dirty.code.push(Op::Return);
            let mut inspect = function(vec![]);
            inspect.frame_size = size; inspect.frame_align = callee_align; inspect.result.size = 0;
            let old_end = 16 + caller_size.max(1);
            let base = (old_end + callee_align - 1) & !(callee_align - 1);
            // Guest integer pointers can observe the interframe padding as
            // well as the callee. All these bytes are live during this call.
            for address in old_end..base + size.max(1) {
                inspect.code.push(Op::Imm { dst: 0, value: address as u128 });
                inspect.code.push(Op::Load { dst: 1, address: 0, size: 1 });
                inspect.code.push(Op::Assert { value: 1, expected: false, message: "dirty frame or padding".into() });
            }
            inspect.code.push(Op::Return);
            let p = program(vec![caller, dirty, inspect]);
            let reference = execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap();
            for persistent in [false, true] {
                let limits = || Limits { jit_resumable_calls: true, jit_persistent_registers: persistent, ..Limits::default() };
                let actual = execute_with_engine(&p, &[], limits(), Engine::Jit).unwrap();
                assert_eq!((actual.value, actual.instructions, actual.peak_memory),
                    (reference.value, reference.instructions, reference.peak_memory));
                assert!(actual.jit_resumable_calls >= 2);
                for instructions in [0, 1, reference.instructions - 1, reference.instructions, reference.instructions + 1] {
                    equal_result(execute_with_engine(&p, &[], Limits { instructions, ..limits() }, Engine::Jit),
                        &execute_with_engine(&p, &[], Limits { instructions, ..Limits::default() }, Engine::Interpreter));
                }
                for memory in [reference.peak_memory - 1, reference.peak_memory, reference.peak_memory + 1] {
                    equal_result(execute_with_engine(&p, &[], Limits { memory, ..limits() }, Engine::Jit),
                        &execute_with_engine(&p, &[], Limits { memory, ..Limits::default() }, Engine::Interpreter));
                }
                for frames in [1, 2, 3] {
                    equal_result(execute_with_engine(&p, &[], Limits { frames, ..limits() }, Engine::Jit),
                        &execute_with_engine(&p, &[], Limits { frames, ..Limits::default() }, Engine::Interpreter));
                }
            }
        }
    }
}

#[test]
fn bulk_zeroing_matches_exact_dirty_ranges_and_preserves_spare_bytes() {
    let mut code = platform::Code::reserve(4096).unwrap();
    let mut entries = vec![];
    for minimum in [0, 64] {
        let mut a = Assembler::default();
        a.mov(11, 2); // owned memory argument; no guest frame is needed
        a.three(0x8b000000, 12, 2, 3); // exclusive end = start + length
        a.zero_range_at_least(minimum).unwrap();
        a.mov(0, 31);
        a.emit(0xd65f03c0); // ret; the helper uses only caller-saved scratch
        entries.push((minimum, code.append(&a.words).unwrap()));
    }
    let mut registers = [0u128; 1];
    for (minimum, entry) in entries {
        for size in (minimum..=256).chain([511, 512, 513, 1023, 1024, 1025, 4095, 4096, 4097]) {
            for alignment in 0..64 {
                // Every byte begins dirty. Full equality checks both the
                // requested initialization and untouched prefix/spare suffix.
                let start = 64 + alignment;
                let mut actual = vec![0xa5u8; start + size + 64];
                let mut expected = actual.clone();
                expected[start..start + size].fill(0);
                // SAFETY: this emitter-owned leaf accesses only the given
                // initialized range, with a true minimum and stable backing.
                // All other pointer arguments are unused by this leaf.
                let result = unsafe {
                    code.call(
                        entry,
                        registers.as_mut_ptr(),
                        0,
                        actual.as_mut_ptr().add(start),
                        size,
                        0,
                        std::ptr::null_mut(),
                        0,
                        std::ptr::null_mut(),
                    )
                };
                assert_eq!(result, 0);
                assert_eq!(
                    actual, expected,
                    "minimum={minimum} size={size} alignment={alignment}"
                );
            }
        }
    }
    // Empty one-past-end is also valid; it must not attempt even one store.
    let mut byte = [0xa5u8];
    unsafe {
        code.call(
            0,
            registers.as_mut_ptr(),
            0,
            byte.as_mut_ptr().add(1),
            0,
            0,
            std::ptr::null_mut(),
            0,
            std::ptr::null_mut(),
        );
    }
    assert_eq!(byte, [0xa5]);
}

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

#[test]
fn retained_call_targets_cover_small_and_large_register_accesses_and_live_spills() {
    let wide = (1u128 << 127) | 0x4567;
    for registers in [8usize, 2048, 2049, 5000] {
        let pointer = registers as Reg - 1;
        let value = registers as Reg - 2;
        let mut root = function(vec![
            Op::Local { dst: pointer, offset: 0 },
            Op::Imm { dst: value, value: wide },
            Op::Store { address: pointer, src: value, size: 16 },
            Op::Call { function: 1, args: vec![pointer], destination: pointer },
            Op::Call { function: 1, args: vec![pointer], destination: pointer },
            Op::Load { dst: 0, address: pointer, size: 16 },
            Op::Binary { dst: 1, overflow: 2, op: Binary::Eq, a: 0, b: value, bits: 128, signed: false },
            Op::Assert { value: 1, expected: true, message: "caller live value or copied result changed".into() },
            Op::Return,
        ]);
        root.registers = registers;
        root.result.size = 16;
        let mut child = function(vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load { dst: 1, address: 0, size: 16 },
            Op::Imm { dst: 2, value: (1u128 << 100) | 0x123 },
            Op::Binary { dst: 3, overflow: 7, op: Binary::Xor, a: 1, b: 2, bits: 128, signed: false },
            Op::Store { address: 0, src: 3, size: 16 },
            Op::Return,
        ]);
        child.args = vec![Slot { offset: 0, size: 16 }];
        child.result.size = 16;
        let p = program(vec![root, child]);
        let reference = execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap();
        assert_eq!(reference.value, wide);
        for persistent in [false, true] {
            let limits = || Limits { jit_resumable_calls: true, jit_persistent_registers: persistent, ..Limits::default() };
            let actual = execute_with_engine(&p, &[], limits(), Engine::Jit).unwrap();
            assert_eq!((actual.value, actual.instructions, actual.peak_memory),
                (reference.value, reference.instructions, reference.peak_memory));
            assert!(actual.jit_resumable_calls > 0);
            for instructions in [0, 1, reference.instructions - 1, reference.instructions] {
                equal_result(execute_with_engine(&p, &[], Limits { instructions, ..limits() }, Engine::Jit),
                    &execute_with_engine(&p, &[], Limits { instructions, ..Limits::default() }, Engine::Interpreter));
            }
        }
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
                                frame_end: frame_end.min(3),
                                working_budget,
                                indirect_layout: std::ptr::null(),
                                indirect_layouts: std::ptr::null(),
                                bridge: tree_bridge::BridgeCursor::new(std::ptr::null_mut(), std::ptr::null()),
                                bridge_instructions: 0, bridge_calls: 0, bridge_entries: 0,
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

#[path="slot_arguments_tests.rs"]
mod slot_arguments;

#[path="budget_register_tests.rs"]
mod budget_register;
