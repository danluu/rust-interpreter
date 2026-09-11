use rust_interp_bytecode::{execute_with_engine, validate, Binary, Engine, Function, Limits,
    Op, Program, Slot, VERSION, FUNCTION_POINTER_TAG, HEAP_POINTER_TAG};

fn engines() -> Vec<(Engine, bool)> {
    let mut result = vec![(Engine::Interpreter, false)];
    if cfg!(all(target_arch="aarch64", target_os="macos")) { result.extend([(Engine::Jit, false), (Engine::Jit, true)]); }
    result
}
fn register(argument: u128) -> Vec<Op> {
    vec![Op::Imm { dst: 0, value: (FUNCTION_POINTER_TAG | 2) as u128 },
        Op::Imm { dst: 1, value: argument }, Op::RegisterTlsDestructor { callback: 0, argument: 1 }]
}
fn fixture(code: Vec<Op>) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![0; 48], thread_locals: vec![Slot { offset: 16, size: 8 }],
        functions: vec![
            Function { name: "root".into(), registers: 8, frame_size: 16, frame_align: 16,
                args: vec![], result: Slot { offset: 0, size: 8 }, code },
            Function { name: "callback".into(), registers: 8, frame_size: 16, frame_align: 16,
                args: vec![Slot { offset: 0, size: 8 }], result: Slot { offset: 0, size: 0 },
                code: vec![
                    Op::Local { dst: 0, offset: 0 }, Op::Load { dst: 1, address: 0, size: 8 },
                    Op::Imm { dst: 2, value: (HEAP_POINTER_TAG + 32) as u128 },
                    Op::Load { dst: 3, address: 2, size: 8 }, Op::Imm { dst: 4, value: 10 },
                    Op::Binary { dst: 3, overflow: 7, op: Binary::Mul, a: 3, b: 4, bits: 64, signed: false },
                    Op::Binary { dst: 3, overflow: 7, op: Binary::Add, a: 3, b: 1, bits: 64, signed: false },
                    Op::Store { address: 2, src: 3, size: 8 },
                    Op::Imm { dst: 2, value: (HEAP_POINTER_TAG + 16) as u128 },
                    Op::Store { address: 2, src: 1, size: 8 }, Op::Return,
                ] },
        ] }
}

#[test]
fn reset_drains_lifo_preserves_statics_and_restores_tls_repeatedly() {
    let mut code = vec![Op::ResetThreadLocals];
    for _ in 0..2 {
        code.extend(register(1)); code.extend(register(2)); code.push(Op::ResetThreadLocals);
        code.extend([
            Op::Imm { dst: 2, value: (HEAP_POINTER_TAG + 16) as u128 },
            Op::Load { dst: 3, address: 2, size: 8 },
            Op::Assert { value: 3, expected: false, message: "TLS restored after callbacks".into() },
        ]);
    }
    code.extend([Op::Imm { dst: 2, value: (HEAP_POINTER_TAG + 32) as u128 },
        Op::Local { dst: 3, offset: 0 }, Op::Copy { dst: 3, src: 2, size: 8 }, Op::Return]);
    let p = fixture(code);
    let expected_steps = p.functions[0].code.len() as u64 + 4 * p.functions[1].code.len() as u64;
    for (engine, resumable) in engines() {
        let result = execute(&p, &[], Limits::default(), engine, resumable).unwrap();
        assert_eq!(result.value, 2121); assert_eq!(result.instructions, expected_steps);
        for instructions in 0..=expected_steps {
            let result = execute(&p, &[], Limits { instructions, ..Limits::default() }, engine, resumable);
            if instructions == expected_steps { assert_eq!(result.unwrap().value, 2121); }
            else { assert!(result.unwrap_err().contains("instruction limit")); }
        }
    }
}

#[test]
fn entry_result_survives_callback_frame_reuse_and_teardown_failure_fails_entry() {
    let mut code = register(9);
    code.extend([Op::Local { dst: 2, offset: 0 }, Op::Imm { dst: 3, value: 42 },
        Op::Store { address: 2, src: 3, size: 8 }, Op::Return]);
    let mut p = fixture(code);
    for (engine, resumable) in engines() {
        let limits = Limits { frames: 1, ..Limits::default() };
        let result = execute(&p, &[], limits, engine, resumable).unwrap();
        assert_eq!(result.value, 42);
        assert_eq!(result.instructions, (p.functions[0].code.len() + p.functions[1].code.len()) as u64);
        let instructions = result.instructions - 1;
        assert!(execute(&p, &[], Limits { instructions, frames: 1, ..Limits::default() }, engine, resumable)
            .unwrap_err().contains("instruction limit"));
    }
    p.functions[1].code = vec![Op::Trap { message: "cleanup failed".into() }];
    for (engine, resumable) in engines() {
        assert!(execute(&p, &[], Limits::default(), engine, resumable).unwrap_err().contains("cleanup failed"));
    }
}

#[test]
fn reset_keeps_root_live_and_nested_callback_calls_use_normal_frames() {
    let mut code = register(1); code.extend([Op::ResetThreadLocals, Op::Return]);
    let mut p = fixture(code);
    let mut nested = p.functions[1].clone(); nested.name = "nested".into(); p.functions.push(nested);
    p.functions[1].code = vec![Op::Local { dst: 0, offset: 0 },
        Op::Call { function: 2, args: vec![0], destination: 0 }, Op::Return];
    for (engine, resumable) in engines() {
        for frames in [1, 2] {
            assert!(execute(&p, &[], Limits { frames, ..Limits::default() }, engine, resumable)
                .unwrap_err().contains("call-depth limit"));
        }
        execute(&p, &[], Limits { frames: 3, ..Limits::default() }, engine, resumable).unwrap();
    }
}

#[test]
fn malformed_registration_and_registration_or_reset_during_teardown_fail() {
    for handle in [0, 1, FUNCTION_POINTER_TAG as u128, (FUNCTION_POINTER_TAG | 99) as u128, 1u128 << 100] {
        let mut code = register(0); code[0] = Op::Imm { dst: 0, value: handle }; code.push(Op::Return);
        for (engine, resumable) in engines() { assert!(execute(&fixture(code.clone()), &[], Limits::default(), engine, resumable).is_err()); }
    }
    let mut code = register(1u128 << 100); code.push(Op::Return);
    for (engine, resumable) in engines() { assert!(execute(&fixture(code.clone()), &[], Limits::default(), engine, resumable)
        .unwrap_err().contains("pointer width")); }
    let mut code = register(0); code.push(Op::Return);
    let p = fixture(code);
    for result in [Slot { offset: 0, size: 1 }, Slot { offset: 0, size: 8 }] {
        let mut bad = p.clone(); bad.functions[1].result = result;
        for (engine, resumable) in engines() { assert!(execute(&bad, &[], Limits::default(), engine, resumable)
            .unwrap_err().contains("signature mismatch")); }
    }
    for callback in [vec![Op::ResetThreadLocals, Op::Return], {
        let mut ops = register(0); ops.push(Op::Return); ops
    }] {
        let mut bad = p.clone(); bad.functions[1].code = callback;
        for (engine, resumable) in engines() { assert!(execute(&bad, &[], Limits::default(), engine, resumable).is_err()); }
    }
    let mut bad = p.clone(); bad.target = "x86_64-unknown-linux-gnu".into(); assert!(validate(&bad).is_err());
    let mut bad = p; bad.functions[0].code[2] = Op::RegisterTlsDestructor { callback: 8, argument: 0 };
    assert!(validate(&bad).is_err());
}

#[test]
fn queued_callback_storage_is_charged_and_released_before_entry_cleanup() {
    let mut code = register(1); code.extend(register(2)); code.push(Op::Return);
    let p = fixture(code);
    // Data16 + static48 + frame16 + registers128 + two callback records32.
    for (engine, resumable) in engines() {
        for memory in [208, 223, 224, 239] {
            assert!(execute(&p, &[], Limits { memory, ..Limits::default() }, engine, resumable)
                .unwrap_err().contains("memory limit"));
        }
        let result = execute(&p, &[], Limits { memory: 240, frames: 1, ..Limits::default() }, engine, resumable).unwrap();
        assert_eq!(result.peak_memory, 112);
    }
}

fn execute(p: &Program, args: &[u128], mut limits: Limits, engine: Engine, resumable: bool)
    -> Result<rust_interp_bytecode::Execution, String> {
    limits.jit_resumable_calls = resumable;
    limits.jit_persistent_registers = resumable;
    execute_with_engine(p, args, limits, engine)
}
