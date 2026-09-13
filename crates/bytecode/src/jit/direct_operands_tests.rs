use super::*;
use crate::{Engine, ExecutionProfile, Limits, Slot, VERSION, execute_profiled, execute_with_engine};

const OPS: [Binary; 6] = [Binary::Add, Binary::Sub, Binary::Mul, Binary::And, Binary::Or, Binary::Xor];
const DIRTY: u128 = 0xfedc_ba98_7654_3210_8123_4567_89ab_cdef;

fn oracle(op: Binary, a: u128, b: u128, bits: u8, signed: bool) -> (u128, bool) {
    macro_rules! integer {
        ($u:ty, $s:ty) => {{
            let (a, b) = (a as $u, b as $u);
            let result = if signed {
                let (a, b) = (a as $s, b as $s);
                match op {
                    Binary::Add => a.overflowing_add(b), Binary::Sub => a.overflowing_sub(b),
                    Binary::Mul => a.overflowing_mul(b), Binary::And => (a & b, false),
                    Binary::Or => (a | b, false), Binary::Xor => (a ^ b, false), _ => unreachable!(),
                }
            } else {
                let (value, overflow) = match op {
                    Binary::Add => a.overflowing_add(b), Binary::Sub => a.overflowing_sub(b),
                    Binary::Mul => a.overflowing_mul(b), Binary::And => (a & b, false),
                    Binary::Or => (a | b, false), Binary::Xor => (a ^ b, false), _ => unreachable!(),
                };
                (value as $s, overflow)
            };
            (result.0 as $u as u128, result.1)
        }};
    }
    match bits { 8 => integer!(u8, i8), 16 => integer!(u16, i16),
        32 => integer!(u32, i32), 64 => integer!(u64, i64), _ => unreachable!() }
}

fn program(op: Binary, bits: u8, signed: bool, dst: Reg, overflow: Reg, returned: Reg) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 64], statics: vec![], thread_locals: vec![], functions: vec![Function {
            name: "direct operands".into(), frame_size: 96, frame_align: 16, registers: 13,
            args: vec![Slot { offset: 16, size: 16 }, Slot { offset: 32, size: 16 }],
            result: Slot { offset: 0, size: 16 },
            code: vec![Op::Local { dst: 0, offset: 16 }, Op::Load { dst: 1, address: 0, size: 16 },
                Op::Local { dst: 2, offset: 32 }, Op::Load { dst: 3, address: 2, size: 16 },
                Op::Binary { dst, overflow, op, a: 1, b: 3, bits, signed },
                Op::Local { dst: 12, offset: 0 }, Op::Store { address: 12, src: returned, size: 16 }, Op::Return],
        }] }
}

fn check_value(p: &Program, args: &[u128], expected: u128) {
    crate::validate(p).unwrap();
    for resumable in [false, true] { for persistent in [false, true] {
        let limits = Limits { jit_resumable_calls: resumable, jit_persistent_registers: persistent,
            instructions: 1024, ..Limits::default() };
        let result = execute_with_engine(p, args, limits, Engine::Jit).unwrap();
        assert_eq!(result.value, expected, "resumable={resumable}, persistent={persistent}");
        assert!(result.jit_instructions > 0);
    }}
}

#[test]
fn direct_selection_preserves_facts_recency_live_inputs_and_exact_encodings() {
    let p = program(Binary::Add, 64, false, 4, 5, 4);
    let mut allocation = values::analyze(&p.functions[0]).unwrap();
    allocation.registers = vec![0, 1, 2];
    let reads = vec![Some((0, 10)); 13];
    let mut a = Assembler { values: Some(&allocation), reads: &reads, ..Assembler::default() };
    assert_eq!(a.low_operand(9, 0), 23);
    a.facts.insert(0, Fact::Imm(1 << 100)); // override stale assigned value
    assert_eq!(a.low_operand(9, 0), 31);
    a.facts.insert(1, Fact::Imm(7));
    assert_eq!(a.low_operand(9, 1), 9);
    assert_eq!(a.words, [0xd28000e9]);
    a.words.clear(); a.facts.insert(2, Fact::Local(32));
    assert_eq!(a.low_operand(10, 2), 10);
    assert_eq!(a.words, [0x9100802a]);
    a.words.clear();
    for lo in [5, 6] {
        a.facts.insert(4, Fact::Cached { lo, high_zero: true });
        assert_eq!(a.low_operand(9, 4), lo);
        assert_eq!(a.cache_recent, (lo - 5) as usize);
    }
    assert!(a.words.is_empty());
    assert_eq!(a.live_in, BTreeSet::from([0, 1, 2, 4]));
    for (op, bits, expected) in [
        (Binary::Add, 64, vec![0x8b1902e9, 0xaa0903e5]),
        (Binary::And, 8, vec![0x8a1902e9, 0xd3401d29, 0xaa0903e5]),
    ] {
        let reads = [Some((0, 2)), Some((0, 2)), Some((1, 2)), None];
        let mut a = Assembler { reads: &reads, ..Assembler::default() };
        a.facts.insert(0, Fact::Physical { lo: 23 });
        a.facts.insert(1, Fact::Physical { lo: 25 });
        assert!(a.direct_binary(2, 3, op, 0, 1, bits));
        assert_eq!(a.words, expected);
    }
    for (op, bits, observed) in [(Binary::Add, 64, true), (Binary::Sub, 8, true),
        (Binary::Mul, 32, true), (Binary::And, 128, false), (Binary::Xor, 1, false),
        (Binary::Div, 64, false), (Binary::Eq, 64, false), (Binary::Shl, 64, false)] {
        let reads = [None, None, None, observed.then_some((0, 1))];
        let mut a = Assembler { reads: &reads, ..Assembler::default() };
        assert!(!a.direct_binary(2, 3, op, 0, 1, bits));
        assert!(a.words.is_empty() && a.live_in.is_empty() && a.defined.is_empty() && a.facts.is_empty());
    }
}

#[test]
fn modular_operands_match_native_rust_with_dirty_bits_and_seeded_pairs() {
    for bits in [8, 16, 32, 64] {
        let sign = 1u128 << (bits - 1);
        let mut pairs = vec![(0, 0), (0, u128::MAX), (u128::MAX, 1), (sign, sign),
            (sign - 1, 1), (sign, u128::MAX), (DIRTY, !DIRTY), (DIRTY, DIRTY),
            (1 << 127, (1 << 100) | 7)];
        let mut seed = 0x6398_e1ac_768d_b3efu128;
        for _ in 0..16 {
            seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
            pairs.push((seed, seed.rotate_left(47)));
        }
        for op in OPS { for signed in [false, true] {
            let p = program(op, bits, signed, 4, 5, 4);
            for &(a, b) in &pairs { check_value(&p, &[a, b], oracle(op, a, b, bits, signed).0); }
        }}
    }
}

#[test]
fn aliases_and_later_source_reads_preserve_full_words_and_checked_overflow() {
    for op in OPS { for bits in [8, 16, 32, 64] { for signed in [false, true] {
        let (a, b) = (DIRTY, !DIRTY);
        let (value, flag) = oracle(op, a, b, bits, signed);
        for dst in [1, 3, 4] { for overflow in [1, 3, 4, 5] {
            let mut regs = [0u128; 6]; regs[1] = a; regs[3] = b;
            regs[dst as usize] = value; regs[overflow as usize] = u128::from(flag);
            for returned in [dst, 1, 3, overflow] {
                let p = program(op, bits, signed, dst, overflow, returned);
                check_value(&p, &[a, b], regs[returned as usize]);
            }
        }}
    }}}
}

fn loop_program() -> Program {
    let mut p = program(Binary::Add, 64, false, 4, 5, 4);
    let callee = program(Binary::Xor, 64, false, 4, 5, 4).functions.remove(0);
    p.functions.push(callee);
    p.functions[1].name = "direct operand callee".into();
    p.functions[0].code.truncate(4);
    p.functions[0].code.extend([
        Op::Imm { dst: 6, value: 0 }, Op::Imm { dst: 7, value: 3 }, Op::Imm { dst: 8, value: 1 },
        Op::Local { dst: 9, offset: 64 },
        Op::Binary { dst: 1, overflow: 10, op: Binary::Add, a: 1, b: 3, bits: 64, signed: false },
        Op::Call { function: 1, args: vec![0, 2], destination: 9 },
        Op::Load { dst: 11, address: 9, size: 16 },
        Op::Binary { dst: 1, overflow: 10, op: Binary::Xor, a: 1, b: 11, bits: 64, signed: false },
        Op::Binary { dst: 6, overflow: 10, op: Binary::Add, a: 6, b: 8, bits: 64, signed: false },
        Op::Binary { dst: 11, overflow: 10, op: Binary::Lt, a: 6, b: 7, bits: 64, signed: false },
        Op::Switch { value: 11, cases: vec![(0, 15)], otherwise: 8 },
        Op::Local { dst: 12, offset: 0 }, Op::Store { address: 12, src: 1, size: 16 }, Op::Return,
    ]);
    p
}

#[test]
fn native_operands_survive_backedges_cache_eviction_and_native_calls() {
    let p = loop_program();
    let allocation = values::analyze(&p.functions[0]).unwrap();
    assert!(allocation.registers.iter().any(|r| [1, 3, 6].contains(r)));
    for (a, b) in [(DIRTY, !DIRTY), (u128::MAX, 7), (0, 0)] {
        let mut value = a as u64;
        for _ in 0..3 { value = value.wrapping_add(b as u64) ^ ((a ^ b) as u64); }
        check_value(&p, &[a, b], value as u128);
    }
}

fn logical(profile: &ExecutionProfile) -> Vec<Vec<u64>> {
    profile.functions.iter().map(|f| {
        let mut result = f.interpreted.clone();
        for (hits, ends) in [(&f.jit_blocks, &f.jit_block_ends), (&f.jit_tree_blocks, &f.jit_tree_block_ends)] {
            for (pc, &count) in hits.iter().enumerate() {
                if count > 0 { for n in &mut result[pc..ends[pc]] { *n += count; } }
            }
        }
        result
    }).collect()
}

#[test]
fn direct_operands_keep_every_budget_tail_and_exact_logical_counts() {
    let p = loop_program();
    let args = [DIRTY, !DIRTY];
    let complete = execute_with_engine(&p, &args, Limits::default(), Engine::Interpreter).unwrap();
    for budget in 0..=complete.instructions + 2 {
        let base = Limits { instructions: budget, ..Limits::default() };
        let reference = execute_profiled(&p, &args, base, Engine::Interpreter);
        for resumable in [false, true] { for persistent in [false, true] { for capacity in [0, MAX_CODE_BYTES] {
            let limits = Limits { instructions: budget, jit_code_bytes: capacity,
                jit_resumable_calls: resumable, jit_persistent_registers: persistent, ..Limits::default() };
            let result = execute_profiled(&p, &args, limits, Engine::Jit);
            match (&reference, result) {
                (Err(expected), Err(actual)) => assert_eq!(&actual, expected),
                (Ok((expected, before)), Ok((actual, after))) => {
                    assert_eq!(actual.value, expected.value);
                    assert_eq!(actual.instructions, expected.instructions);
                    assert_eq!(logical(&after), logical(before));
                }
                (expected, actual) => panic!("budget={budget}: {expected:?} != {actual:?}"),
            }
        }}}
    }
}
