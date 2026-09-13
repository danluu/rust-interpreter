use super::*;
use crate::{Engine, Limits, Slot, VERSION, execute_profiled, execute_with_engine};

const VALUE: u128 = 0xfedc_ba98_7654_3210_8123_4567_89ab_cdef;

fn oracle(op: Binary, input: u128, count: u128, bits: u8, signed: bool) -> u128 {
    macro_rules! integer {
        ($u:ty, $s:ty) => {{
            let value = input as $u;
            let count = count as u32;
            (match op {
                Binary::Shl => value.wrapping_shl(count),
                Binary::Shr if signed => (value as $s).wrapping_shr(count) as $u,
                Binary::Shr => value.wrapping_shr(count),
                Binary::RotateLeft => value.rotate_left(count),
                Binary::RotateRight => value.rotate_right(count),
                _ => unreachable!(),
            }) as u128
        }};
    }
    match bits { 8 => integer!(u8, i8), 16 => integer!(u16, i16),
        32 => integer!(u32, i32), 64 => integer!(u64, i64), _ => unreachable!() }
}

fn program(op: Binary, bits: u8, signed: bool, count: u128, dst: Reg, overflow: Reg) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 64], statics: vec![], thread_locals: vec![], functions: vec![Function {
            name: "immediate-shift".into(), frame_size: 64, frame_align: 16, registers: 8,
            args: vec![Slot { offset: 16, size: 16 }], result: Slot { offset: 0, size: 16 },
            code: vec![Op::Local { dst: 0, offset: 16 }, Op::Load { dst: 1, address: 0, size: 16 },
                Op::Imm { dst: 2, value: count },
                Op::Binary { dst, overflow, op, a: 1, b: 2, bits, signed },
                Op::Assert { value: overflow, expected: false, message: "shift overflow".into() },
                Op::Local { dst: 5, offset: 0 }, Op::Store { address: 5, src: dst, size: 16 },
                Op::Return],
        }] }
}

#[test]
fn immediate_counts_and_exact_encodings_preserve_fallback_boundaries() {
    let mut a = Assembler::default();
    for value in [0, 1, 31, 32, 63, 64, 127, 1 << 100, (1 << 127) | 13, u128::MAX] {
        a.facts.insert(2, Fact::Imm(value));
        for bits in [8, 16, 32, 64] {
            for op in [Binary::Shl, Binary::Shr, Binary::RotateLeft, Binary::RotateRight] {
                let eligible = matches!(op, Binary::Shl | Binary::Shr) || bits >= 32;
                assert_eq!(a.immediate_shift_amount(op, bits, 2),
                    eligible.then_some((value & u128::from(bits - 1)) as u8));
            }
        }
        for bits in [0, 1, 7, 128] { assert_eq!(a.immediate_shift_amount(Binary::Shl, bits, 2), None); }
        assert_eq!(a.immediate_shift_amount(Binary::Add, 64, 2), None);
    }
    for fact in [Fact::Local(13), Fact::Physical { lo: 23 }, Fact::Cached { lo: 5, high_zero: true }] {
        a.facts.insert(2, fact); assert_eq!(a.immediate_shift_amount(Binary::Shl, 64, 2), None);
    }
    a.facts.clear(); assert_eq!(a.immediate_shift_amount(Binary::Shl, 64, 2), None);
    for (op, bits, signed, count, expected) in [
        (Binary::Shl, 64, false, 13, vec![0xd373c929]),
        (Binary::Shr, 64, false, 13, vec![0xd34dfd29]),
        (Binary::Shr, 64, true, 13, vec![0x934dfd29]),
        (Binary::Shr, 8, true, 3, vec![0x93401d29, 0x9343fd29]),
        (Binary::RotateRight, 64, false, 13, vec![0x93c93529]),
        (Binary::RotateLeft, 64, false, 13, vec![0x93c9cd29]),
        (Binary::RotateRight, 32, false, 13, vec![0x13893529]),
        (Binary::RotateLeft, 32, false, 13, vec![0x13894d29]),
        (Binary::Shl, 64, false, 0, vec![]),
        (Binary::RotateLeft, 32, false, 0, vec![]),
    ] {
        a.words.clear(); a.immediate_shift(op, bits, signed, count); assert_eq!(a.words, expected);
    }
}

#[test]
fn native_immediate_shifts_match_rust_for_every_count_residue_and_full_output_word() {
    for bits in [8, 16, 32, 64] {
        let counts: Vec<u128> = (0..u128::from(bits)).chain([u128::from(bits), u128::from(bits)+1,
            127, (1 << 127) | 13, u128::MAX]).collect();
        for op in [Binary::Shl, Binary::Shr, Binary::RotateLeft, Binary::RotateRight] {
            for signed in [false, true] { for &count in &counts {
                let p = program(op, bits, signed, count, 3, 4);
                crate::validate(&p).unwrap();
                for value in [VALUE, !VALUE, 0, u128::MAX] {
                    let expected = oracle(op, value, count, bits, signed);
                    for resumable in [false, true] { for persistent in [false, true] {
                        let limits = Limits { jit_resumable_calls: resumable, jit_persistent_registers: persistent,
                            instructions: 64, ..Limits::default() };
                        let result = execute_with_engine(&p, &[value], limits, Engine::Jit).unwrap();
                        assert_eq!(result.value, expected, "{op:?} bits={bits} signed={signed} count={count}");
                        assert!(result.jit_instructions > 0);
                    }}
                }
            }}
        }
    }
}

#[test]
fn immediate_shift_aliases_keep_value_then_overflow_assignment() {
    for op in [Binary::Shl, Binary::Shr, Binary::RotateLeft, Binary::RotateRight] {
        for (dst, overflow) in [(3, 4), (1, 4), (2, 4), (3, 1), (3, 2), (1, 2), (2, 1), (3, 3), (1, 1), (2, 2)] {
            for bits in [8, 32, 64] { for count in [0, 1, 63, 64, u128::MAX] {
                let p = program(op, bits, true, count, dst, overflow);
                let expected = if dst == overflow { 0 } else { oracle(op, VALUE, count, bits, true) };
                assert_eq!(execute_with_engine(&p, &[VALUE], Limits::default(), Engine::Interpreter).unwrap().value, expected);
                for resumable in [false, true] { for persistent in [false, true] {
                    let limits = Limits { jit_resumable_calls: resumable, jit_persistent_registers: persistent,
                        ..Limits::default() };
                    assert_eq!(execute_with_engine(&p, &[VALUE], limits, Engine::Jit).unwrap().value, expected);
                }}
            }}
        }
    }
}

#[test]
fn immediate_shift_budget_tails_preserve_logical_work_and_errors() {
    for op in [Binary::Shl, Binary::Shr, Binary::RotateLeft, Binary::RotateRight] {
        for bits in [8, 32, 64] { for count in [0, 1, u128::MAX] {
            let p = program(op, bits, true, count, 3, 4);
            for budget in 0..=12 {
                let reference = execute_profiled(&p, &[VALUE], Limits { instructions: budget, ..Limits::default() }, Engine::Interpreter);
                for resumable in [false, true] { for persistent in [false, true] {
                    let actual = execute_profiled(&p, &[VALUE], Limits { instructions: budget,
                        jit_resumable_calls: resumable, jit_persistent_registers: persistent,
                        ..Limits::default() }, Engine::Jit);
                    match (&reference, actual) {
                        (Err(expected), Err(actual)) => assert_eq!(*expected, actual),
                        (Ok((expected, original)), Ok((actual, observed))) => {
                            assert_eq!((actual.value, actual.instructions), (expected.value, expected.instructions));
                            for (before, after) in original.functions.iter().zip(observed.functions.iter()) {
                                let mut logical = after.interpreted.clone();
                                for (counts, ends) in [(&after.jit_blocks, &after.jit_block_ends),
                                                      (&after.jit_tree_blocks, &after.jit_tree_block_ends)] {
                                    for (start, &hits) in counts.iter().enumerate() {
                                        if hits > 0 { for n in &mut logical[start..ends[start]] { *n += hits; } }
                                    }
                                }
                                assert_eq!(logical, before.interpreted);
                            }
                        }
                        _ => panic!("result differs at budget {budget}"),
                    }
                }}
            }
        }}
    }
}
