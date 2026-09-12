#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{
    Binary, Engine, Function, Limits, Op, Program, Slot, VERSION, execute_with_engine,
};

fn fixture(op: Binary, bits: u8, signed: bool, dst: u32, overflow: u32) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![Function {
            name: "checked-division".into(),
            frame_size: 48,
            frame_align: 16,
            registers: dst.max(overflow).max(6) as usize + 1,
            args: vec![
                Slot {
                    offset: 0,
                    size: 16,
                },
                Slot {
                    offset: 16,
                    size: 16,
                },
            ],
            result: Slot {
                offset: 32,
                size: 16,
            },
            code: vec![
                Op::Local { dst: 0, offset: 0 },
                Op::Local { dst: 1, offset: 16 },
                Op::Load {
                    dst: 2,
                    address: 0,
                    size: 16,
                },
                Op::Load {
                    dst: 3,
                    address: 1,
                    size: 16,
                },
                Op::Binary {
                    dst,
                    overflow,
                    op,
                    a: 2,
                    b: 3,
                    bits,
                    signed,
                },
                Op::Local { dst: 6, offset: 32 },
                Op::Store {
                    address: 6,
                    src: dst,
                    size: 16,
                },
                Op::Local { dst: 6, offset: 40 },
                Op::Store {
                    address: 6,
                    src: overflow,
                    size: 1,
                },
                Op::Return,
            ],
        }],
    }
}

#[test]
fn division_and_remainder_match_vm_at_boundaries_with_aliases_and_high_bits() {
    for bits in [8, 16, 32, 64] {
        let sign = 1u128 << (bits - 1);
        let max = (1u128 << bits) - 1;
        let mut pairs = vec![
            (0, 0),
            (0, 1),
            (1, 0),
            (max, 1),
            (max, max),
            (sign, 1),
            (sign, max),
            (sign, sign),
            (sign - 1, 1),
            (sign - 1, 2),
            (1, sign),
            (u128::MAX, u128::MAX),
            (123, 1u128 << bits),
            (sign | (1u128 << 127), max | (1u128 << 126)),
            (max, 3),
        ];
        let mut state = 0xd37c_aa68_51be_937fu64;
        for _ in 0..16 {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            let a = state as u128 | (0xfedc_ba98_7654_3210u128 << 64);
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            pairs.push((a, state as u128 | (0x0123_4567_89ab_cdefu128 << 64)));
        }
        for signed in [false, true] {
            for op in [Binary::Div, Binary::Rem] {
                for (dst, overflow) in [
                    (4, 5),
                    (2, 3),
                    (3, 2),
                    (4, 2),
                    (2, 2),
                    (4, 4),
                    (0, 1),
                    (4097, 4098),
                ] {
                    let p = fixture(op, bits, signed, dst, overflow);
                    for &(a, b) in &pairs {
                        let expected = execute_with_engine(
                            &p,
                            &[a, b],
                            Limits::default(),
                            Engine::Interpreter,
                        );
                        let got = execute_with_engine(&p, &[a, b], Limits::default(), Engine::Jit);
                        match (expected, got) {
                            (Ok(expected), Ok(got)) => {
                                assert_eq!(
                                    got.value, expected.value,
                                    "{op:?} {bits} signed={signed}, dst={dst}, flag={overflow}, a={a:x}, b={b:x}"
                                );
                                assert_eq!(got.instructions, expected.instructions);
                                assert_eq!(got.jit_instructions + 1, got.instructions);
                            }
                            (Err(expected), Err(got)) => assert_eq!(
                                got, expected,
                                "{op:?} {bits} signed={signed}, a={a:x}, b={b:x}"
                            ),
                            _ => panic!(
                                "engine outcomes differ: {op:?} {bits} signed={signed}, a={a:x}, b={b:x}"
                            ),
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn division_faults_and_success_preserve_instruction_budget_boundaries() {
    for op in [Binary::Div, Binary::Rem] {
        let p = fixture(op, 64, true, 4, 5);
        for args in [[19, 3], [19, 0], [1u128 << 63, u64::MAX as u128]] {
            for instructions in 0..=10 {
                let limits = || Limits {
                    instructions,
                    ..Limits::default()
                };
                let expected = execute_with_engine(&p, &args, limits(), Engine::Interpreter);
                let got = execute_with_engine(&p, &args, limits(), Engine::Jit);
                match (expected, got) {
                    (Ok(a), Ok(b)) => {
                        assert_eq!(a.value, b.value);
                        assert_eq!(a.instructions, b.instructions);
                    }
                    (Err(a), Err(b)) => assert_eq!(a, b),
                    _ => panic!("engine budget outcomes differ"),
                }
            }
        }
    }
}

#[test]
fn first_arithmetic_fault_wins_inside_one_generated_region() {
    for zero_first in [false, true] {
        let mut p = fixture(Binary::Div, 64, true, 4, 5);
        let zero = Op::Binary {
            dst: 0,
            overflow: 1,
            op: Binary::Div,
            a: 5,
            b: 4,
            bits: 64,
            signed: true,
        };
        let overflow = Op::Binary {
            dst: 0,
            overflow: 1,
            op: Binary::Rem,
            a: 2,
            b: 3,
            bits: 64,
            signed: true,
        };
        let code = &mut p.functions[0].code;
        *code = vec![
            Op::Imm {
                dst: 2,
                value: 1u128 << 63,
            },
            Op::Imm {
                dst: 3,
                value: u64::MAX as u128,
            },
            Op::Imm { dst: 4, value: 0 },
            Op::Imm { dst: 5, value: 1 },
        ];
        if zero_first {
            code.extend([zero, overflow]);
        } else {
            code.extend([overflow, zero]);
        }
        code.push(Op::Return);
        let want = if zero_first {
            "integer division by zero"
        } else {
            "signed division overflow"
        };
        for engine in [Engine::Interpreter, Engine::Jit] {
            let got = execute_with_engine(&p, &[0, 0], Limits::default(), engine)
                .err()
                .unwrap();
            assert_eq!(got, want);
        }
    }
}

#[test]
fn arithmetic_and_memory_faults_keep_program_order() {
    for memory_first in [false, true] {
        let mut p = fixture(Binary::Div, 64, false, 4, 5);
        let memory = Op::Load {
            dst: 3,
            address: 2,
            size: 1,
        };
        let zero = Op::Binary {
            dst: 0,
            overflow: 1,
            op: Binary::Div,
            a: 4,
            b: 5,
            bits: 64,
            signed: false,
        };
        let code = &mut p.functions[0].code;
        *code = vec![
            Op::Imm {
                dst: 2,
                value: u128::MAX,
            },
            Op::Imm { dst: 4, value: 1 },
            Op::Imm { dst: 5, value: 0 },
        ];
        if memory_first {
            code.extend([memory, zero]);
        } else {
            code.extend([zero, memory]);
        }
        code.push(Op::Return);
        let interpreted = execute_with_engine(&p, &[0, 0], Limits::default(), Engine::Interpreter)
            .err()
            .unwrap();
        let jitted = execute_with_engine(&p, &[0, 0], Limits::default(), Engine::Jit)
            .err()
            .unwrap();
        if memory_first {
            assert_ne!(interpreted, "integer division by zero");
            assert_eq!(jitted, "JIT guest memory access failed");
        } else {
            assert_eq!(interpreted, "integer division by zero");
            assert_eq!(jitted, interpreted);
        }
    }
}
