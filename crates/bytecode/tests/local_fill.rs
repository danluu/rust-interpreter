#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{
    Binary, Engine, Function, Limits, Op, Program, Slot, VERSION, execute_profiled,
    execute_with_engine,
};

fn program(code: Vec<Op>, frame_size: usize, registers: usize) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![Function {
            name: "local-fill".into(),
            frame_size,
            frame_align: 16,
            registers,
            args: vec![],
            result: Slot { offset: 0, size: 8 },
            code,
        }],
    }
}

fn checksum(
    offset: usize,
    length: usize,
    value: u128,
    register: u32,
    padding: usize,
) -> (Program, u128, usize) {
    let frame = (offset + length + 17).max(640);
    let mut bytes = vec![0x5au8; frame];
    bytes[offset..offset + length].fill(value as u8);
    let expected = bytes
        .iter()
        .enumerate()
        .map(|(i, b)| (i as u128 + 1) * u128::from(*b))
        .sum::<u128>()
        + u128::from(value as u8)
        + length as u128;
    // The large initial sentinel fill stays in the VM. The second fill is the
    // candidate, and every byte before, inside and after it contributes to the
    // checksum, including unaligned starts and partial tails.
    let mut code = vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Imm {
            dst: 1,
            value: 0x5a,
        },
        Op::Imm {
            dst: 2,
            value: frame as u128,
        },
        Op::FillBytes {
            address: 0,
            value: 1,
            size: 2,
        },
    ];
    code.extend((0..padding).map(|_| Op::Imm { dst: 9, value: 0 }));
    code.extend([
        Op::Local {
            dst: register,
            offset,
        },
        Op::Imm {
            dst: register + 1,
            value,
        },
        Op::Imm {
            dst: register + 2,
            value: length as u128,
        },
    ]);
    let fill = code.len();
    code.push(Op::FillBytes {
        address: register,
        value: register + 1,
        size: register + 2,
    });
    // A split immediately before FillBytes must still leave at least three
    // native operations (fill, this observable definition, and the jump).
    code.push(Op::Imm { dst: 11, value });
    code.push(Op::Jump {
        target: code.len() + 1,
    });
    code.extend([
        Op::Local { dst: 0, offset: 0 },
        Op::Imm { dst: 1, value: 1 },
        Op::Imm {
            dst: 2,
            value: frame as u128,
        },
        Op::Imm { dst: 3, value: 0 },
        Op::Imm { dst: 6, value: 1 },
    ]);
    let head = code.len();
    code.extend([
        Op::Load {
            dst: 4,
            address: 0,
            size: 1,
        },
        Op::Binary {
            dst: 8,
            overflow: 7,
            op: Binary::Mul,
            a: 4,
            b: 1,
            bits: 64,
            signed: false,
        },
        Op::Binary {
            dst: 3,
            overflow: 7,
            op: Binary::Add,
            a: 3,
            b: 8,
            bits: 64,
            signed: false,
        },
        Op::Binary {
            dst: 0,
            overflow: 7,
            op: Binary::Add,
            a: 0,
            b: 6,
            bits: 64,
            signed: false,
        },
        Op::Binary {
            dst: 1,
            overflow: 7,
            op: Binary::Add,
            a: 1,
            b: 6,
            bits: 64,
            signed: false,
        },
        Op::Binary {
            dst: 2,
            overflow: 7,
            op: Binary::Sub,
            a: 2,
            b: 6,
            bits: 64,
            signed: false,
        },
        Op::Switch {
            value: 2,
            cases: vec![(0, head + 7)],
            otherwise: head,
        },
        // All three setup registers are live across the fill, a branch, and
        // the checksum loop. They must still have their original full values.
        Op::Local { dst: 9, offset },
        Op::Binary {
            dst: 10,
            overflow: 7,
            op: Binary::Eq,
            a: register,
            b: 9,
            bits: 64,
            signed: false,
        },
        Op::Assert {
            value: 10,
            expected: true,
            message: "local address live-out".into(),
        },
        Op::Binary {
            dst: 10,
            overflow: 7,
            op: Binary::Eq,
            a: register + 1,
            b: 11,
            bits: 128,
            signed: false,
        },
        Op::Assert {
            value: 10,
            expected: true,
            message: "full-width byte-source live-out".into(),
        },
        Op::Cast {
            dst: 9,
            src: register + 1,
            from: 128,
            to: 8,
            signed: false,
        },
        Op::Binary {
            dst: 3,
            overflow: 7,
            op: Binary::Add,
            a: 3,
            b: 9,
            bits: 64,
            signed: false,
        },
        Op::Binary {
            dst: 3,
            overflow: 7,
            op: Binary::Add,
            a: 3,
            b: register + 2,
            bits: 64,
            signed: false,
        },
        Op::Local { dst: 0, offset: 0 },
        Op::Store {
            address: 0,
            src: 3,
            size: 8,
        },
        Op::Return,
    ]);
    (program(code, frame, register as usize + 3), expected, fill)
}

fn check(p: &Program, expected: u128, fill: usize, native: bool, budgets: &[u64]) {
    let reference = execute_with_engine(p, &[], Limits::default(), Engine::Interpreter).unwrap();
    assert_eq!(reference.value, expected);
    for engine in [Engine::Interpreter, Engine::Jit] {
        let ordinary = execute_with_engine(p, &[], Limits::default(), engine).unwrap();
        let (observed, profile) = execute_profiled(p, &[], Limits::default(), engine).unwrap();
        assert_eq!(ordinary.value, expected);
        assert_eq!(observed.value, expected);
        assert_eq!(ordinary.instructions, reference.instructions);
        assert_eq!(observed.instructions, reference.instructions);
        assert_eq!(ordinary.peak_memory, reference.peak_memory);
        assert_eq!(observed.peak_memory, reference.peak_memory);
        if engine == Engine::Jit {
            assert_eq!(profile.functions[0].interpreted[fill] == 0, native);
        }
        for budget in budgets
            .iter()
            .copied()
            .chain([reference.instructions - 1, reference.instructions])
        {
            let limits = Limits {
                instructions: budget,
                ..Limits::default()
            };
            let got = execute_with_engine(p, &[], limits, engine);
            if budget < reference.instructions {
                assert_eq!(got.unwrap_err(), "interpreter instruction limit exceeded");
            } else {
                assert_eq!(got.unwrap().value, expected);
            }
        }
    }
}

#[test]
fn fills_preserve_every_width_unaligned_tails_and_high_byte_bits() {
    for length in [
        0, 1, 2, 3, 7, 8, 9, 15, 16, 17, 31, 32, 33, 127, 255, 511, 512, 513,
    ] {
        for offset in [0, 3, 19] {
            for value in [0, 0x33, 0xff, (1u128 << 117) | 0x81] {
                let (p, expected, fill) = checksum(offset, length, value, 16, 0);
                check(&p, expected, fill, length <= 512, &[]);
            }
        }
    }
}

#[test]
fn region_splits_preserve_setup_live_outs_and_exact_budget_tails() {
    // The preceding unsupported sentinel fill starts the next native region
    // at PC4. Split at each point in the setup/fill sequence around 1024 ops.
    for padding in [1020, 1021, 1022, 1023, 1024, 2045, 2046, 2047] {
        let (p, expected, fill) = checksum(8193, 511, (1u128 << 91) | 0xa5, 5000, padding);
        check(
            &p,
            expected,
            fill,
            true,
            &[
                0,
                1,
                3,
                4,
                1027,
                1028,
                1029,
                fill as u64,
                fill as u64 + 1,
                fill as u64 + 2,
            ],
        );
    }
}

#[test]
fn branches_that_bypass_literal_definitions_keep_dynamic_semantics() {
    for (target, expected, native) in [
        (4, 0, true),
        (5, 0x33333333, false),
        (6, 0x09090909, false),
        (7, 9, false),
    ] {
        let p = program(
            vec![
                Op::Local { dst: 0, offset: 0 },
                Op::Imm { dst: 1, value: 9 },
                Op::Imm { dst: 2, value: 1 },
                Op::Jump { target },
                Op::Local { dst: 0, offset: 8 },
                Op::Imm {
                    dst: 1,
                    value: 0x33,
                },
                Op::Imm { dst: 2, value: 4 },
                Op::FillBytes {
                    address: 0,
                    value: 1,
                    size: 2,
                },
                Op::Imm { dst: 3, value: 0 },
                Op::Imm { dst: 3, value: 1 },
                Op::Return,
            ],
            16,
            4,
        );
        check(&p, expected, 7, native, &[0, 1, 2, 3, 4, 5, 6, 7]);
    }
}

#[test]
fn unproven_aliases_and_out_of_frame_fills_match_vm_errors() {
    for (address, value, size, offset, length, byte) in [
        (0, 0, 2, 0, 1, 17),
        (0, 1, 0, 0, 3, 0x33),
        (0, 1, 1, 0, 2, 0x33),
        (0, 1, 2, 16, 1, 0x33),
        (0, 1, 2, 15, 2, 0x33),
        (0, 1, 2, 16, 0, 0x33),
    ] {
        let p = program(
            vec![
                Op::Local {
                    dst: address,
                    offset,
                },
                Op::Imm {
                    dst: value,
                    value: byte,
                },
                Op::Imm {
                    dst: size,
                    value: length,
                },
                Op::FillBytes {
                    address,
                    value,
                    size,
                },
                Op::Imm { dst: 3, value: 0 },
                Op::Imm { dst: 3, value: 1 },
                Op::Return,
            ],
            16,
            4,
        );
        for budget in 0..=7 {
            let limits = || Limits {
                instructions: budget,
                ..Limits::default()
            };
            let expected =
                execute_with_engine(&p, &[], limits(), Engine::Interpreter).map(|r| r.value);
            assert_eq!(
                execute_with_engine(&p, &[], limits(), Engine::Jit).map(|r| r.value),
                expected
            );
            assert_eq!(
                execute_profiled(&p, &[], limits(), Engine::Jit).map(|(r, _)| r.value),
                expected
            );
        }
    }
}
