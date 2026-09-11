use super::*;
use crate::{Engine, Limits, Slot, VERSION, execute_profiled, execute_with_engine};

const LIVE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;

fn expected(value: u128, bits: u8) -> u128 {
    (match bits {
        8 => (value as u8).count_ones(),
        16 => (value as u16).count_ones(),
        32 => (value as u32).count_ones(),
        64 => (value as u64).count_ones(),
        128 => value.count_ones(),
        _ => unreachable!(),
    }) as u128
}

fn program(code: Vec<Op>) -> Program {
    Program {
        version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 64], statics: vec![], thread_locals: vec![],
        functions: vec![Function {
            name: "population_count".into(), frame_size: 320, frame_align: 16,
            registers: 7, args: vec![], result: Slot { offset: 0, size: 16 }, code,
        }],
    }
}

#[test]
fn native_population_counts_match_rust_with_aliases_and_vector_copy_neighbors() {
    let mut inputs: Vec<u128> = (0..=255).collect();
    inputs.extend([u128::MAX, LIVE, !LIVE, u64::MAX as u128, 1 << 127]);
    for bit in 0..128 { inputs.extend([1 << bit, !(1 << bit)]); }
    let mut seed = LIVE;
    for _ in 0..512 {
        seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
        inputs.push(seed);
    }
    for bits in [8, 16, 32, 64] {
        for alias in [false, true] {
            let dst = if alias { 0 } else { 6 };
            let p = program(vec![
                Op::Copy { dst: 2, src: 1, size: 128 },
                Op::Unary { dst, src: 0, bits, op: Unary::CountOnes },
                Op::Copy { dst: 1, src: 2, size: 128 },
                Op::Store { address: 5, src: dst, size: 16 },
                // Force a VM exit with a separate full-width register live.
                Op::Unary { dst: 4, src: 3, bits: 128, op: Unary::CountOnes },
                Op::Return,
            ]);
            crate::validate(&p).unwrap();
            for profiled in [false, true] {
                let mut jit = Jit::new(&p, profiled, MAX_CODE_BYTES).unwrap();
                jit.ensure_function(0).unwrap();
                let block = jit.blocks[0][0].unwrap();
                assert_eq!(block.end, 4);
                for &input in &inputs {
                    let mut memory: Vec<u8> = (0..512).map(|i| (i * 43 + 7) as u8).collect();
                    let mut reference = memory.clone();
                    reference.copy_within(96..224, 224);
                    reference.copy_within(224..352, 96);
                    reference[64..80].copy_from_slice(&expected(input, bits).to_le_bytes());
                    let mut registers = [input, 96, 224, LIVE, !LIVE, 64, u128::MAX];
                    let mut hits = [0; 6];
                    let result = unsafe { jit.run(block, 6, 4,
                        if profiled { hits.as_mut_ptr() } else { std::ptr::null_mut() },
                        registers.as_mut_ptr(), 64, memory.as_mut_ptr(), memory.len(), 64,
                        std::ptr::null_mut(), 0) }.unwrap();
                    assert_eq!(result, (4, 4));
                    assert_eq!(memory, reference, "bits={bits} input={input:x} alias={alias}");
                    assert_eq!(registers[dst as usize], expected(input, bits));
                    if !alias { assert_eq!(registers[0], input); }
                    assert_eq!(registers[3], LIVE);
                    assert_eq!(registers[4], !LIVE);
                    assert_eq!(hits, [u64::from(profiled), 0, 0, 0, 0, 0]);
                }
            }
        }
    }
}

#[test]
fn population_count_loops_preserve_all_budget_tails_and_128_bit_fallback() {
    for bits in [8, 16, 32, 64, 128] {
        for input in [0, 1, u128::MAX, LIVE, 1 << 127, 1 << 63] {
            let p = program(vec![
                Op::Imm { dst: 0, value: input },
                Op::Imm { dst: 1, value: 3 },
                Op::Imm { dst: 2, value: 1 },
                Op::Local { dst: 3, offset: 0 },
                Op::Unary { dst: 4, src: 0, bits, op: Unary::CountOnes },
                Op::Store { address: 3, src: 4, size: 16 },
                Op::Binary { dst: 1, overflow: 5, op: Binary::Sub,
                    a: 1, b: 2, bits: 64, signed: false },
                Op::Switch { value: 1, cases: vec![(0, 9)], otherwise: 4 },
                Op::Trap { message: "unreachable branch".into() },
                Op::Return,
            ]);
            for budget in 0..=18 {
                for engine in [Engine::Interpreter, Engine::Jit] {
                    let limits = || Limits { instructions: budget, ..Limits::default() };
                    let normal = execute_with_engine(&p, &[], limits(), engine);
                    let observed = execute_profiled(&p, &[], limits(), engine);
                    if budget < 17 {
                        assert_eq!(normal.unwrap_err(), "interpreter instruction limit exceeded");
                        assert_eq!(observed.unwrap_err(), "interpreter instruction limit exceeded");
                    } else {
                        let normal = normal.unwrap();
                        let (observed, profile) = observed.unwrap();
                        assert_eq!(normal.value, expected(input, bits));
                        assert_eq!(observed.value, expected(input, bits));
                        assert_eq!(normal.instructions, 17);
                        assert_eq!(observed.instructions, 17);
                        assert_eq!(normal.jit_instructions, observed.jit_instructions);
                        assert_eq!(profile.functions[0].interpreted[4],
                            if engine == Engine::Interpreter || bits == 128 { 3 } else { 0 });
                        if engine == Engine::Jit && bits <= 64 {
                            assert_eq!(normal.jit_entries, 1);
                            assert_eq!(normal.jit_instructions, 16);
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn population_count_regions_preserve_assertion_fault_and_budget_order() {
    for bits in [8, 16, 32, 64, 128] {
        let p = program(vec![
            Op::Imm { dst: 0, value: 0 },
            Op::Unary { dst: 1, src: 0, bits, op: Unary::CountOnes },
            Op::Assert { value: 1, expected: true, message: "count was zero".into() },
            Op::Trap { message: "later failure".into() },
            Op::Return,
        ]);
        for budget in 0..=6 {
            let limits = || Limits { instructions: budget, ..Limits::default() };
            let reference = execute_with_engine(&p, &[], limits(), Engine::Interpreter).unwrap_err();
            if budget < 3 { assert_eq!(reference, "interpreter instruction limit exceeded"); }
            else { assert!(reference.contains("count was zero")); }
            for engine in [Engine::Interpreter, Engine::Jit] {
                assert_eq!(execute_with_engine(&p, &[], limits(), engine).unwrap_err(), reference);
                assert_eq!(execute_profiled(&p, &[], limits(), engine).unwrap_err(), reference);
            }
        }
    }
}
