use super::*;
use crate::{Engine, Limits, Slot, VERSION, execute_with_engine};

#[test]
fn register_transfers_use_pairs_only_at_profitable_offset_boundaries() {
    for load in [false, true] {
        for reg in [0, 1, 31, 32, 2047, 2048, 4095, 65520] {
            let mut a = Assembler::default();
            a.transfer_register_pair(load, reg, 23, 24);
            let pair = if load { 0xa9400000 } else { 0xa9000000 };
            let scalar = if load { 0xf9400000 } else { 0xf9000000 };
            if reg < 32 {
                assert_eq!(a.words, [pair | (reg * 2 << 15) | (24 << 10) | 23]);
            } else if reg < 2048 {
                assert_eq!(a.words, [scalar | (reg * 2 << 10) | 23,
                    scalar | ((reg * 2 + 1) << 10) | 24]);
            } else {
                assert_eq!(*a.words.last().unwrap(), pair | (24 << 10) | (16 << 5) | 23);
                let mut old = Assembler::default();
                for high in [false, true] {
                    let (base, offset) = old.reg_address(reg, high);
                    old.emit(scalar | (offset << 10) | (base << 5) | (23 + u32::from(high)));
                }
                assert!(a.words.len() < old.words.len());
            }
        }
    }
    let mut a = Assembler::default();
    a.raw_spill(31, 5, 31);
    assert_eq!(a.words, [0xa9000000 | (62 << 15) | (31 << 10) | 5]);
}

#[test]
fn register_pairs_preserve_both_words_across_vm_exits_and_every_budget_tail() {
    const MASK: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;
    for target in [0, 1, 31, 32, 2047, 2048, 4095, 65520] {
        let addr = target + 1;
        let temp = target + 2;
        let mask = target + 3;
        let overflow = target + 4;
        let barrier = Op::Binary { dst: target + 5, overflow: target + 6,
            op: Binary::Mul, a: mask, b: mask, bits: 128, signed: false };
        assert!(!supported(&barrier)); // Force live values through a VM boundary.
        let program = Program {
            version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
            data: vec![0; 64], statics: vec![], thread_locals: vec![],
            functions: vec![Function { name: "paired-registers".into(),
                frame_size: 64, frame_align: 16, registers: target as usize + 7,
                args: vec![Slot { offset: 0, size: 16 }], result: Slot { offset: 0, size: 16 },
                code: vec![Op::Local { dst: addr, offset: 0 },
                    Op::Load { dst: target, address: addr, size: 16 },
                    Op::Load { dst: temp, address: addr, size: 16 },
                    Op::Imm { dst: mask, value: MASK },
                    Op::Binary { dst: temp, overflow, op: Binary::Xor, a: temp, b: mask, bits: 128, signed: false },
                    barrier,
                    Op::Binary { dst: target, overflow, op: Binary::Sub, a: target, b: temp, bits: 128, signed: false },
                    Op::Store { address: addr, src: target, size: 16 }, Op::Return] }],
        };
        crate::validate(&program).unwrap();
        for value in [0, 1 << 64, MASK, !MASK] {
            let reference = execute_with_engine(&program, &[value], Limits::default(), Engine::Interpreter).unwrap();
            assert_eq!(reference.value, value.wrapping_sub(value ^ MASK));
            for persistent in [false, true] {
                for budget in 0..=reference.instructions + 1 {
                    let limits = || Limits { instructions: budget, jit_resumable_calls: true,
                        jit_persistent_registers: persistent, ..Limits::default() };
                    let expected = execute_with_engine(&program, &[value],
                        Limits { instructions: budget, ..Limits::default() }, Engine::Interpreter);
                    let actual = execute_with_engine(&program, &[value], limits(), Engine::Jit);
                    match (expected, actual) {
                        (Ok(a), Ok(b)) => {
                            assert_eq!((a.value, a.instructions, a.peak_memory), (b.value, b.instructions, b.peak_memory));
                            assert!(b.jit_instructions > 0);
                        }
                        (Err(a), Err(b)) => assert_eq!(a, b),
                        pair => panic!("paired transfer mismatch: {pair:?}"),
                    }
                }
            }
        }
    }
}
