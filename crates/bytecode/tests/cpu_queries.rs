use rust_interp_bytecode::{execute_with_engine, execute_profiled, validate, Binary, Engine, Function, Limits, Op, Program, Slot, VERSION};

fn program(alias: bool) -> Program {
    let name = b"hw.optional.arm.FEAT_AES\0";
    let mut data = vec![0; 16]; data.extend_from_slice(name);
    let result = if alias { 0 } else { 7 };
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data, statics: vec![], thread_locals: vec![],
        functions: vec![Function {
            name: "cpu-query".into(), registers: 16, frame_size: 48, frame_align: 16,
            args: vec![], result: Slot { offset: 0, size: 16 },
            code: vec![
                Op::Imm { dst: 0, value: 16 },
                Op::Local { dst: 1, offset: 24 },
                Op::Local { dst: 2, offset: 32 },
                Op::Imm { dst: 3, value: 0 },
                Op::Imm { dst: 4, value: 4 },
                Op::Imm { dst: 5, value: 0xfedcba9876543210_0123456789abcdef },
                Op::Store { address: 2, src: 4, size: 8 },
                Op::CpuFeatureQuery { dst: result, name: 0, output: 1, output_len: 2, new_data: 3, new_len: 3 },
                Op::Imm { dst: 8, value: 0 },
                Op::Binary { dst: 9, overflow: 10, op: Binary::Eq, a: result, b: 8, bits: 32, signed: false },
                Op::Assert { value: 9, expected: true, message: "query failed".into() },
                Op::Load { dst: 11, address: 2, size: 8 },
                Op::Binary { dst: 9, overflow: 10, op: Binary::Eq, a: 11, b: 4, bits: 64, signed: false },
                Op::Assert { value: 9, expected: true, message: "wrong returned length".into() },
                Op::Load { dst: 12, address: 1, size: 4 },
                // Keep a full-width value live across the host primitive.
                Op::Binary { dst: 13, overflow: 14, op: Binary::Xor, a: 5, b: 12, bits: 128, signed: false },
                Op::Local { dst: 15, offset: 0 },
                Op::Store { address: 15, src: 13, size: 16 },
                Op::Return,
            ],
        }],
    }
}

#[test]
#[cfg(all(target_os="macos", target_arch="aarch64"))]
fn native_boundaries_aliasing_profiles_and_exact_budgets() {
    for alias in [false, true] {
        let p = program(alias);
        let expected = execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap();
        assert_eq!(expected.instructions, p.functions[0].code.len() as u64);
        for engine in [Engine::Interpreter, Engine::Jit] {
            let (result, _) = execute_profiled(&p, &[], Limits::default(), engine).unwrap();
            assert_eq!(result.value, expected.value);
            assert_eq!(result.instructions, expected.instructions);
            for budget in 0..=expected.instructions+1 {
                let limits = Limits { instructions: budget, ..Limits::default() };
                let result = execute_with_engine(&p, &[], limits, engine);
                if budget < expected.instructions {
                    assert!(result.unwrap_err().contains("instruction limit"));
                } else { assert_eq!(result.unwrap().value, expected.value); }
            }
        }
    }
}

#[test]
fn every_cpu_query_register_is_validated_and_encoding_roundtrips() {
    let p = program(false);
    let bytes = bincode::serialize(&p).unwrap();
    let copy: Program = bincode::deserialize(&bytes).unwrap();
    validate(&copy).unwrap();
    assert_eq!(bincode::serialize(&copy).unwrap(), bytes);
    for index in 0..6 {
        let mut p = program(false);
        let mut registers = [7, 0, 1, 2, 3, 3];
        registers[index] = 16;
        p.functions[0].code[7] = Op::CpuFeatureQuery { dst: registers[0], name: registers[1],
            output: registers[2], output_len: registers[3], new_data: registers[4], new_len: registers[5] };
        assert!(validate(&p).is_err(), "register {index}");
    }
}
