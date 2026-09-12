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
            name: "observed-overflow".into(),
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
fn observed_overflow_matches_vm_at_boundaries_and_with_register_aliasing() {
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
        ];
        let mut state = 0xd37c_aa68_51be_937fu64;
        for _ in 0..16 {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            let a = state as u128 | (0xfedc_ba98_7654_3210u128 << 64);
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            pairs.push((a, state as u128 | (0x0123_4567_89ab_cdefu128 << 64)));
        }
        for signed in [false, true] {
            for op in [Binary::Add, Binary::Sub, Binary::Mul] {
                // Result and flag may overwrite either operand or each other.
                // The last pair also exercises large register spill offsets.
                for (dst, overflow) in
                    [(4, 5), (2, 3), (3, 2), (4, 2), (2, 2), (4, 4), (4097, 4098)]
                {
                    let p = fixture(op, bits, signed, dst, overflow);
                    for &(a, b) in &pairs {
                        let expected = execute_with_engine(
                            &p,
                            &[a, b],
                            Limits::default(),
                            Engine::Interpreter,
                        )
                        .unwrap();
                        let got = execute_with_engine(&p, &[a, b], Limits::default(), Engine::Jit)
                            .unwrap();
                        assert_eq!(
                            got.value, expected.value,
                            "{op:?} {bits} signed={signed}, dst={dst}, flag={overflow}, a={a:x}, b={b:x}"
                        );
                        assert_eq!(got.instructions, expected.instructions);
                        // Every operation except Return must run in generated
                        // code; merely entering a JIT block would not prove this.
                        assert_eq!(got.jit_instructions + 1, got.instructions);
                    }
                }
            }
        }
    }
}

#[test]
fn instruction_budget_preserves_the_vm_boundary_with_checked_arithmetic() {
    let p = fixture(Binary::Mul, 64, true, 4, 5);
    for instructions in 0..=10 {
        let limits = || Limits {
            instructions,
            ..Limits::default()
        };
        let expected = execute_with_engine(
            &p,
            &[1u128 << 63, u64::MAX as u128],
            limits(),
            Engine::Interpreter,
        );
        let got = execute_with_engine(&p, &[1u128 << 63, u64::MAX as u128], limits(), Engine::Jit);
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
