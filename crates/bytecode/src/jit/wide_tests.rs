use super::*;
use crate::{Engine, Limits, Slot, VERSION, execute_profiled, execute_with_engine};

const LIVE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;

// Independent native Rust oracle; do not use the bytecode implementation here.
fn expected(op: Binary, a: u128, b: u128, signed: bool) -> (u128, bool) {
    if matches!(op, Binary::Sub) {
        return if signed {
            let (value, overflow) = (a as i128).overflowing_sub(b as i128);
            (value as u128, overflow)
        } else { a.overflowing_sub(b) };
    }
    let order = if signed { (a as i128).cmp(&(b as i128)) } else { a.cmp(&b) };
    use std::cmp::Ordering::*;
    (match op {
        Binary::Eq => u128::from(order == Equal),
        Binary::Ne => u128::from(order != Equal),
        Binary::Lt => u128::from(order == Less),
        Binary::Le => u128::from(order != Greater),
        Binary::Gt => u128::from(order == Greater),
        Binary::Ge => u128::from(order != Less),
        Binary::Cmp => match order { Less => 255, Equal => 0, Greater => 1 },
        _ => unreachable!(),
    }, false)
}

fn program(registers: Reg, args: Vec<Slot>, code: Vec<Op>) -> Program {
    Program {
        version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 64], statics: vec![], thread_locals: vec![],
        functions: vec![Function {
            name: "wide_integer".into(), frame_size: 64, frame_align: 16,
            registers: registers as usize, args, result: Slot { offset: 0, size: 16 }, code,
        }],
    }
}

#[test]
fn wide_native_results_match_rust_including_aliases_and_far_registers() {
    let boundaries = [0, 1, 2, u64::MAX as u128, 1 << 64, (1 << 64) + 1,
        (1 << 127) - 1, 1 << 127, (1 << 127) + 1, u128::MAX - 1, u128::MAX, LIVE, !LIVE];
    let mut pairs = Vec::new();
    for a in boundaries { for b in boundaries { pairs.push((a, b)); } }
    for bit in 0..128 { pairs.extend([(1 << bit, 1), (0, 1 << bit), (1 << bit, 1 << bit)]); }
    let mut seed = LIVE;
    for _ in 0..512 {
        let a = seed;
        seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
        pairs.push((a, seed));
    }
    for op in [Binary::Sub, Binary::Eq, Binary::Ne, Binary::Lt, Binary::Le,
        Binary::Gt, Binary::Ge, Binary::Cmp] {
        for signed in [false, true] {
            for offset in [0, 2050] {
                for (dst, overflow) in [(2, 3), (0, 3), (1, 3), (2, 0), (2, 1),
                    (0, 1), (1, 0), (2, 2), (0, 0), (1, 1)] {
                    let dst = offset + dst;
                    let overflow = offset + overflow;
                    let p = program(offset + 8, vec![], vec![
                        Op::Binary { dst, overflow, op, a: offset, b: offset + 1, bits: 128, signed },
                        Op::Store { address: offset + 4, src: dst, size: 16 },
                        Op::Store { address: offset + 5, src: overflow, size: 16 },
                        // Read overflow after the native exit so a deferred zero
                        // must be spilled, even when the output aliases an input.
                        Op::Unary { dst: offset + 6, src: overflow, bits: 128, op: Unary::CountOnes },
                        Op::Return,
                    ]);
                    crate::validate(&p).unwrap();
                    for profiled in [false, true] {
                        let mut jit = Jit::new(&p, profiled, MAX_CODE_BYTES).unwrap();
                        jit.ensure_function(0).unwrap();
                        let block = jit.blocks[0][0].unwrap();
                        assert_eq!(block.end, 3);
                        let mut registers = vec![LIVE; (offset + 8) as usize];
                        for &(a, b) in &pairs {
                            registers[offset as usize..].copy_from_slice(&[a, b, !LIVE, !LIVE, 64, 80, LIVE, !LIVE]);
                            let (value, flag) = expected(op, a, b, signed);
                            let result = if dst == overflow { u128::from(flag) } else { value };
                            let mut memory = [0u8; 128];
                            let mut hits = [0u64; 5];
                            let exit = unsafe { jit.run(block, 5, 3,
                                if profiled { hits.as_mut_ptr() } else { std::ptr::null_mut() },
                                registers.as_mut_ptr(), 64, memory.as_mut_ptr(), memory.len(), 64,
                                std::ptr::null_mut(), 0) }.unwrap();
                            assert_eq!(exit, (3, 3));
                            assert_eq!(u128::from_le_bytes(memory[64..80].try_into().unwrap()), result,
                                "{op:?} signed={signed} a={a:x} b={b:x} dst={dst} overflow={overflow}");
                            assert_eq!(u128::from_le_bytes(memory[80..96].try_into().unwrap()), u128::from(flag));
                            assert_eq!(registers[dst as usize], result);
                            assert_eq!(registers[overflow as usize], u128::from(flag));
                            assert_eq!(&registers[(offset + 6) as usize..], &[LIVE, !LIVE]);
                            if dst != offset && overflow != offset { assert_eq!(registers[offset as usize], a); }
                            if dst != offset + 1 && overflow != offset + 1 { assert_eq!(registers[(offset + 1) as usize], b); }
                            assert_eq!(hits, [u64::from(profiled), 0, 0, 0, 0]);
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn wide_subtraction_without_observed_overflow_and_with_identical_inputs() {
    for same in [false, true] {
        for signed in [false, true] {
            let p = program(5, vec![], vec![
                Op::Binary { dst: 0, overflow: 2, op: Binary::Sub, a: 0,
                    b: if same { 0 } else { 1 }, bits: 128, signed },
                Op::Store { address: 3, src: 0, size: 16 },
                Op::Store { address: 3, src: 0, size: 16 },
                Op::Return,
            ]);
            crate::validate(&p).unwrap();
            let mut jit = Jit::new(&p, false, MAX_CODE_BYTES).unwrap();
            jit.ensure_function(0).unwrap();
            for a in [0, 1, 1 << 64, 1 << 127, u128::MAX, LIVE] {
                for b in [0, 1, (1 << 64) + 1, 1 << 127, u128::MAX, !LIVE] {
                    let mut registers = [a, b, LIVE, 64, !LIVE];
                    let mut memory = [0u8; 128];
                    let exit = unsafe { jit.run(jit.blocks[0][0].unwrap(), 4, 3,
                        std::ptr::null_mut(), registers.as_mut_ptr(), 64,
                        memory.as_mut_ptr(), memory.len(), 64, std::ptr::null_mut(), 0) }.unwrap();
                    assert_eq!(exit, (3, 3));
                    assert_eq!(u128::from_le_bytes(memory[64..80].try_into().unwrap()),
                        expected(Binary::Sub, a, if same { a } else { b }, signed).0);
                    assert_eq!(registers[4], !LIVE);
                }
            }
        }
    }
}

#[test]
fn wide_loop_preserves_every_budget_tail_and_logical_profile() {
    let p = program(8, vec![Slot { offset: 16, size: 16 }], vec![
        Op::Local { dst: 3, offset: 0 },
        Op::Local { dst: 4, offset: 16 },
        Op::Load { dst: 0, address: 4, size: 16 },
        Op::Imm { dst: 1, value: 1 },
        Op::Imm { dst: 2, value: (1 << 64) - 2 },
        Op::Binary { dst: 0, overflow: 5, op: Binary::Sub, a: 0, b: 1, bits: 128, signed: false },
        Op::Binary { dst: 6, overflow: 7, op: Binary::Le, a: 0, b: 2, bits: 128, signed: false },
        Op::Store { address: 3, src: 0, size: 16 },
        Op::Switch { value: 6, cases: vec![(1, 10)], otherwise: 5 },
        Op::Trap { message: "unreachable".into() },
        Op::Return,
    ]);
    for budget in 0..=20 {
        for capacity in [0, MAX_CODE_BYTES] {
            for engine in [Engine::Interpreter, Engine::Jit] {
                let limits = || Limits { instructions: budget, jit_code_bytes: capacity, ..Limits::default() };
                let normal = execute_with_engine(&p, &[(1 << 64) + 1], limits(), engine);
                let observed = execute_profiled(&p, &[(1 << 64) + 1], limits(), engine);
                if budget < 18 {
                    assert_eq!(normal.unwrap_err(), "interpreter instruction limit exceeded");
                    assert_eq!(observed.unwrap_err(), "interpreter instruction limit exceeded");
                } else {
                    let normal = normal.unwrap();
                    let (observed, profile) = observed.unwrap();
                    assert_eq!(normal.value, (1 << 64) - 2);
                    assert_eq!(observed.value, normal.value);
                    assert_eq!(normal.instructions, 18);
                    assert_eq!(observed.instructions, 18);
                    assert_eq!(normal.jit_instructions, observed.jit_instructions);
                    let f = &profile.functions[0];
                    let mut counts = f.interpreted.clone();
                    for (start, &hits) in f.jit_blocks.iter().enumerate() {
                        if hits != 0 { for count in &mut counts[start..f.jit_block_ends[start]] { *count += hits; } }
                    }
                    assert_eq!(counts, [1, 1, 1, 1, 1, 3, 3, 3, 3, 0, 1]);
                    if engine == Engine::Jit && capacity != 0 {
                        assert_eq!(normal.jit_entries, 1);
                        assert_eq!(normal.jit_instructions, 17);
                    } else { assert_eq!(normal.jit_instructions, 0); }
                }
            }
        }
    }
}

#[test]
fn wide_comparison_assertions_preserve_fault_order() {
    let p = program(6, vec![Slot { offset: 16, size: 16 }], vec![
        Op::Local { dst: 0, offset: 16 },
        Op::Load { dst: 1, address: 0, size: 16 },
        Op::Imm { dst: 2, value: 0 },
        Op::Binary { dst: 3, overflow: 4, op: Binary::Le, a: 1, b: 2, bits: 128, signed: false },
        Op::Assert { value: 3, expected: true, message: "wide comparison failed".into() },
        Op::Trap { message: "later failure".into() },
        Op::Return,
    ]);
    for budget in 0..=8 {
        let limits = || Limits { instructions: budget, ..Limits::default() };
        let reference = execute_with_engine(&p, &[1 << 127], limits(), Engine::Interpreter).unwrap_err();
        if budget < 5 { assert_eq!(reference, "interpreter instruction limit exceeded"); }
        else { assert!(reference.contains("wide comparison failed")); }
        for engine in [Engine::Interpreter, Engine::Jit] {
            assert_eq!(execute_with_engine(&p, &[1 << 127], limits(), engine).unwrap_err(), reference);
            assert_eq!(execute_profiled(&p, &[1 << 127], limits(), engine).unwrap_err(), reference);
        }
    }
}
