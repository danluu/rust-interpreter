use rust_interp_bytecode::{
    Engine, FloatBinary, FloatConversion, FloatUnary, Function, Limits, Op, Program, Slot, VERSION,
    execute_with_engine, validate,
};

fn program(operation: Op) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![Function {
            name: "floating-point operation".into(),
            frame_size: 48,
            frame_align: 16,
            registers: 7,
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
                operation,
                Op::Local { dst: 6, offset: 32 },
                Op::Store {
                    address: 6,
                    src: 4,
                    size: 16,
                },
                Op::Return,
            ],
        }],
    }
}

fn values(operation: Op, a: u128, b: u128) -> Vec<u128> {
    let p = program(operation);
    let mut engines = vec![Engine::Interpreter];
    if cfg!(all(target_arch = "aarch64", target_os = "macos")) {
        engines.push(Engine::Jit);
    }
    engines
        .into_iter()
        .map(|engine| {
            execute_with_engine(&p, &[a, b], Limits::default(), engine)
                .unwrap()
                .value
        })
        .collect()
}

#[test]
fn ieee_special_values_and_unordered_comparisons() {
    for v in values(
        Op::FloatBinary {
            dst: 4,
            op: FloatBinary::Div,
            a: 2,
            b: 3,
            bits: 64,
        },
        1f64.to_bits() as u128,
        (-0f64).to_bits() as u128,
    ) {
        assert_eq!(v, f64::NEG_INFINITY.to_bits() as u128);
    }
    for v in values(
        Op::FloatBinary {
            dst: 4,
            op: FloatBinary::Div,
            a: 2,
            b: 3,
            bits: 32,
        },
        0,
        0,
    ) {
        assert!(f32::from_bits(v as u32).is_nan());
    }
    for (op, want) in [
        (FloatBinary::Eq, 0),
        (FloatBinary::Ne, 1),
        (FloatBinary::Lt, 0),
        (FloatBinary::Le, 0),
        (FloatBinary::Gt, 0),
        (FloatBinary::Ge, 0),
    ] {
        for v in values(
            Op::FloatBinary {
                dst: 4,
                op,
                a: 2,
                b: 3,
                bits: 64,
            },
            f64::NAN.to_bits() as u128,
            1f64.to_bits() as u128,
        ) {
            assert_eq!(v, want);
        }
    }
    for v in values(
        Op::FloatUnary {
            dst: 4,
            op: FloatUnary::Neg,
            src: 2,
            bits: 64,
        },
        0,
        0,
    ) {
        assert_eq!(v, 1u128 << 63);
    }
    for v in values(
        Op::FloatUnary {
            dst: 4,
            op: FloatUnary::Abs,
            src: 2,
            bits: 32,
        },
        1u128 << 31,
        0,
    ) {
        assert_eq!(v, 0);
    }
}

#[test]
fn integer_casts_saturate_and_avoid_double_rounding() {
    let above_half = (1u128 << 100) + (1u128 << 76) + 1;
    for v in values(
        Op::FloatConvert {
            dst: 4,
            kind: FloatConversion::IntToFloat { signed: false },
            src: 2,
            from: 128,
            to: 32,
        },
        above_half,
        0,
    ) {
        assert_eq!(v, 0x7180_0001);
    }
    for (a, want) in [
        (f64::NAN, 0),
        (f64::INFINITY, 127),
        (f64::NEG_INFINITY, 128),
        (-127.75, 129),
        (128.0, 127),
    ] {
        for v in values(
            Op::FloatConvert {
                dst: 4,
                kind: FloatConversion::FloatToInt { signed: true },
                src: 2,
                from: 64,
                to: 8,
            },
            a.to_bits() as u128,
            0,
        ) {
            assert_eq!(v, want);
        }
    }
    for (a, want) in [(f64::INFINITY, u128::MAX), (-1.0, 0), (f64::NAN, 0)] {
        for v in values(
            Op::FloatConvert {
                dst: 4,
                kind: FloatConversion::FloatToInt { signed: false },
                src: 2,
                from: 64,
                to: 128,
            },
            a.to_bits() as u128,
            0,
        ) {
            assert_eq!(v, want);
        }
    }
}

#[test]
fn malformed_float_instructions_are_rejected_before_execution() {
    for bits in [0, 8, 16, 128] {
        assert!(
            validate(&program(Op::FloatBinary {
                dst: 4,
                op: FloatBinary::Add,
                a: 2,
                b: 3,
                bits
            }))
            .is_err()
        );
        assert!(
            validate(&program(Op::FloatUnary {
                dst: 4,
                op: FloatUnary::Abs,
                src: 2,
                bits
            }))
            .is_err()
        );
    }
    for (kind, from, to) in [
        (FloatConversion::FloatToFloat, 32, 128),
        (FloatConversion::FloatToInt { signed: true }, 16, 64),
        (FloatConversion::IntToFloat { signed: false }, 7, 32),
    ] {
        assert!(
            validate(&program(Op::FloatConvert {
                dst: 4,
                kind,
                src: 2,
                from,
                to
            }))
            .is_err()
        );
    }
    assert!(
        validate(&program(Op::FloatUnary {
            dst: 7,
            op: FloatUnary::Abs,
            src: 2,
            bits: 32
        }))
        .is_err()
    );
}
