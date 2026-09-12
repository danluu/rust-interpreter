use super::*;
use crate::{Engine, ExecutionProfile, Limits, Slot, VERSION, execute_profiled, execute_with_engine};

fn function(code: Vec<Op>, registers: usize) -> Function {
    Function { name: "rematerialization".into(), frame_size: 64, frame_align: 16,
        registers, args: vec![], result: Slot { offset: 0, size: 16 }, code }
}

fn proof_function() -> Function {
    function(vec![
        Op::Imm { dst: 0, value: (1 << 127) | 123 },
        Op::Local { dst: 1, offset: 0 }, Op::Jump { target: 3 },
        Op::Assert { value: 0, expected: true, message: "wide".into() },
        Op::Store { address: 1, src: 0, size: 16 },
        Op::Assert { value: 0, expected: true, message: "still wide".into() },
        Op::Load { dst: 2, address: 1, size: 16 }, Op::Return,
    ], 3)
}

#[test]
fn uniform_values_free_pairs_but_conflicts_and_initial_reads_do_not() {
    let f = proof_function();
    let a = analyze_rematerialized(&f).unwrap();
    assert_eq!(a.rematerialized[0], Some(Rematerialized::Imm((1 << 127) | 123)));
    assert_eq!(a.rematerialized[1], Some(Rematerialized::Local(0)));
    assert!(!a.registers.contains(&0) && !a.registers.contains(&1));
    assert!(analyze(&f).unwrap().rematerialized.is_empty());
    for op in [Op::Imm { dst: 0, value: 4 }, Op::Local { dst: 0, offset: 8 },
               Op::Load { dst: 0, address: 1, size: 8 }] {
        let mut changed = f.clone();
        // An unreachable writer still rules out this whole-function proof.
        changed.code.extend([op, Op::Return]);
        assert_eq!(analyze_rematerialized(&changed).unwrap().rematerialized[0], None);
    }
    let mut initial = f.clone();
    initial.code[0] = Op::Assert { value: 0, expected: false, message: "initial zero".into() };
    initial.code.extend([Op::Imm { dst: 0, value: 123 }, Op::Return]);
    assert_eq!(analyze_rematerialized(&initial).unwrap().rematerialized[0], None);
}

#[test]
fn rematerialization_accepts_uniform_loop_definitions_and_has_a_fixed_bound() {
    let mut f = proof_function();
    f.code[7] = Op::Jump { target: 0 };
    assert_eq!(analyze_rematerialized(&f).unwrap().rematerialized[0],
               Some(Rematerialized::Imm((1 << 127) | 123)));
    let n = MAX_REMATERIALIZED + 7;
    let mut code: Vec<_> = (0..n).map(|r| Op::Imm { dst: r as Reg, value: r as u128 + 1 }).collect();
    code.push(Op::Jump { target: n + 1 });
    for _ in 0..2 { for r in 0..n {
        code.push(Op::Assert { value: r as Reg, expected: true, message: "constant".into() });
    } }
    code.push(Op::Return);
    let f = function(code, n);
    assert_eq!(analyze_rematerialized(&f).unwrap().rematerialized.iter().flatten().count(), MAX_REMATERIALIZED);
    assert!(analyze_with_options(&f, 0, true).is_none());
}

#[test]
fn rematerialization_proof_matches_enumerated_paths_on_seeded_diamonds() {
    // Independently execute each possible path through small acyclic graphs,
    // keeping the initial zero value and the actual value at every read.
    let mut seed = 0x48da_0931_b672u64;
    for _ in 0..96 {
        seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
        let first = seed as u128 | 1;
        let second = if seed & 1 == 0 { first } else { first ^ (1 << 99) };
        let f = function(vec![
            Op::Imm { dst: 0, value: first },
            Op::Switch { value: 1, cases: vec![(0, 2)], otherwise: 4 },
            Op::Imm { dst: 0, value: second }, Op::Jump { target: 5 },
            Op::Imm { dst: 0, value: first },
            Op::Assert { value: 0, expected: true, message: "first read".into() },
            Op::Assert { value: 0, expected: true, message: "second read".into() }, Op::Return,
        ], 2);
        let a = analyze_rematerialized(&f).unwrap();
        let mut reads = vec![];
        let mut pending = vec![(0, [0u128; 2])];
        while let Some((pc, mut regs)) = pending.pop() {
            match &f.code[pc] {
                Op::Imm { dst, value } => { regs[*dst as usize] = *value; pending.push((pc + 1, regs)); }
                Op::Switch { cases, otherwise, .. } => {
                    for target in cases.iter().map(|(_, pc)| *pc).chain([*otherwise]) { pending.push((target, regs)); }
                }
                Op::Jump { target } => pending.push((*target, regs)),
                Op::Assert { value, .. } => { reads.push(regs[*value as usize]); pending.push((pc + 1, regs)); }
                Op::Return => {}, _ => unreachable!(),
            }
        }
        let uniform = reads.iter().all(|&value| value == first);
        assert_eq!(a.rematerialized[0], uniform.then_some(Rematerialized::Imm(first)));
    }
}

fn program(functions: Vec<Function>) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        functions, data: vec![0; 16], statics: vec![], thread_locals: vec![] }
}

fn logical(profile: &ExecutionProfile) -> Vec<Vec<u64>> {
    profile.functions.iter().map(|f| {
        let mut counts = f.interpreted.clone();
        for (pc, &hits) in f.jit_blocks.iter().enumerate() {
            if hits != 0 { for count in &mut counts[pc..f.jit_block_ends[pc]] { *count += hits; } }
        }
        counts
    }).collect()
}

#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
fn compare(p: &Program, budget: u64, capacity: usize) {
    let limits = || Limits { instructions: budget, jit_code_bytes: capacity, ..Limits::default() };
    let reference = execute_profiled(p, &[], limits(), Engine::Interpreter);
    for persistent in [false, true] {
        let native = || Limits { jit_resumable_calls: true, jit_persistent_registers: persistent, ..limits() };
        let actual = execute_profiled(p, &[], native(), Engine::Jit);
        let plain = execute_with_engine(p, &[], native(), Engine::Jit);
        match &reference {
            Err(error) => { assert_eq!(&actual.unwrap_err(), error); assert_eq!(&plain.unwrap_err(), error); }
            Ok((reference, expected_profile)) => {
                let (actual, profile) = actual.unwrap(); let plain = plain.unwrap();
                for execution in [&actual, &plain] {
                    assert_eq!(execution.value, reference.value);
                    assert_eq!(execution.instructions, reference.instructions);
                    assert_eq!(execution.peak_memory, reference.peak_memory);
                    if capacity == MAX_CODE_BYTES { assert!(execution.jit_instructions > 0); }
                }
                assert_eq!(logical(&profile), logical(expected_profile));
            }
        }
    }
}

#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
#[test]
fn live_values_are_published_before_interpreted_allocation_and_budget_exits() {
    let mut f = proof_function();
    f.registers = 6;
    f.code.splice(3..3, [
        Op::Imm { dst: 3, value: 8 }, Op::Imm { dst: 4, value: 8 },
        Op::Jump { target: 6 },
        Op::Allocate { dst: 5, size: 3, align: 4, zeroed: true },
        Op::Deallocate { pointer: 5, size: 3, align: 4 },
    ]);
    let p = program(vec![f]);
    crate::validate(&p).unwrap();
    let total = execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap().instructions;
    for budget in 0..=total + 1 { for capacity in [0, 256, MAX_CODE_BYTES] { compare(&p, budget, capacity); } }
}

#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
#[test]
fn caller_constants_and_frame_addresses_survive_direct_and_indirect_calls() {
    let child = function(vec![Op::Local { dst: 0, offset: 0 },
        Op::Imm { dst: 1, value: 0x1234 }, Op::Store { address: 0, src: 1, size: 16 }, Op::Return], 2);
    for indirect in [false, true] {
        let mut root = proof_function(); root.registers = 4;
        root.code[2] = Op::Imm { dst: 3, value: (crate::FUNCTION_POINTER_TAG | 2) as u128 };
        root.code.insert(3, if indirect {
            Op::CallIndirect { callee: 3, args: vec![], arg_sizes: vec![], destination: 1, result_size: 16 }
        } else { Op::Call { function: 1, args: vec![], destination: 1 } });
        let p = program(vec![root, child.clone()]); crate::validate(&p).unwrap();
        let total = execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap().instructions;
        for budget in 0..=total + 1 { for capacity in [0, 256, 2048, MAX_CODE_BYTES] { compare(&p, budget, capacity); } }
    }
}

#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
#[test]
fn seeded_valid_native_graphs_preserve_values_profiles_and_initial_zeros() {
    let mut seed = 0xfbc2_54e0_u64;
    for index in 0..64 {
        seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
        let wide = ((seed as u128) << 64) | !seed as u128;
        let f = function(vec![
            Op::Assert { value: 4, expected: false, message: "initial register".into() },
            Op::Imm { dst: 0, value: wide }, Op::Local { dst: 1, offset: 0 },
            Op::Imm { dst: 2, value: (seed & 1) as u128 },
            Op::Switch { value: 2, cases: vec![(0, 5)], otherwise: 7 },
            Op::Imm { dst: 3, value: wide }, Op::Jump { target: 8 },
            Op::Imm { dst: 3, value: if index % 3 == 0 { !wide } else { wide } },
            Op::Store { address: 1, src: 3, size: 16 },
            Op::Binary { dst: 4, overflow: 5, op: Binary::Xor, a: 0, b: 3, bits: 128, signed: false },
            Op::Store { address: 1, src: 4, size: 16 },
            Op::Assert { value: 0, expected: true, message: "wide constant".into() },
            Op::Assert { value: 3, expected: true, message: "branch value".into() }, Op::Return,
        ], 6);
        let p = program(vec![f]); crate::validate(&p).unwrap();
        compare(&p, 64, MAX_CODE_BYTES);
    }
}
