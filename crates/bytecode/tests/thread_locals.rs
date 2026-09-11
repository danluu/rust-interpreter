use rust_interp_bytecode::{execute_with_engine, validate, Engine, Function, Limits, Op, Program, Slot, VERSION, HEAP_POINTER_TAG};

fn fixture(code: Vec<Op>) -> Program {
    let mut statics = vec![0; 48];
    statics[16..24].copy_from_slice(&7u64.to_le_bytes());
    statics[32..40].copy_from_slice(&11u64.to_le_bytes());
    Program {
        version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 32], statics, thread_locals: vec![Slot { offset: 16, size: 8 }],
        functions: vec![Function {
            name: "tls".into(), registers: 8, frame_size: 16, frame_align: 16,
            args: vec![], result: Slot { offset: 0, size: 16 }, code,
        }],
    }
}
fn engines() -> Vec<Engine> {
    let mut engines = vec![Engine::Interpreter];
    if cfg!(all(target_arch="aarch64",target_os="macos")) { engines.push(Engine::Jit); }
    engines
}
#[test]
fn reset_restores_only_tls_and_preserves_shared_statics() {
    let p = fixture(vec![
        Op::Imm { dst: 0, value: (HEAP_POINTER_TAG + 16) as u128 },
        Op::Imm { dst: 1, value: (HEAP_POINTER_TAG + 32) as u128 },
        Op::Imm { dst: 2, value: 99 },
        Op::Store { address: 0, src: 2, size: 8 },
        Op::Store { address: 1, src: 2, size: 8 },
        Op::ResetThreadLocals,
        Op::Local { dst: 3, offset: 0 }, Op::Copy { dst: 3, src: 0, size: 8 },
        Op::Local { dst: 4, offset: 8 }, Op::Copy { dst: 4, src: 1, size: 8 },
        Op::Return,
    ]);
    for engine in engines() {
        assert_eq!(execute_with_engine(&p, &[], Limits::default(), engine).unwrap().value, 7 | 99u128 << 64);
    }
}
#[test]
fn nested_reset_is_rejected() {
    let mut p = fixture(vec![Op::ResetThreadLocals, Op::Return]);
    let mut root = p.functions[0].clone();
    root.code = vec![Op::Local { dst: 0, offset: 0 }, Op::Call { function: 0, args: vec![], destination: 0 }, Op::Return];
    p.functions.push(root); p.entry = 1;
    for engine in engines() {
        assert!(execute_with_engine(&p, &[], Limits::default(), engine).unwrap_err().contains("root frame"));
    }
}
#[test]
fn malformed_tls_ranges_are_rejected() {
    for slots in [vec![Slot { offset: 0, size: 1 }], vec![Slot { offset: 16, size: 0 }],
        vec![Slot { offset: 47, size: 2 }], vec![Slot { offset: usize::MAX, size: 2 }],
        vec![Slot { offset: 16, size: 8 }, Slot { offset: 20, size: 8 }]] {
        let mut p = fixture(vec![Op::Return]); p.thread_locals = slots;
        assert!(validate(&p).is_err());
    }
}
#[test]
fn random_bytes_checks_complete_destination_before_host_call() {
    for (address, size) in [(16, 1), (31, 2), (usize::MAX, 2), (HEAP_POINTER_TAG as usize + 47, 2)] {
        let p = fixture(vec![Op::Imm { dst: 0, value: address as u128 }, Op::Imm { dst: 1, value: size },
            Op::RandomBytes { dst: 0, address: 0, size: 1 }, Op::Return]);
        for engine in engines() { assert!(execute_with_engine(&p, &[], Limits::default(), engine).is_err()); }
    }
}

#[test]
#[cfg(target_os="macos")]
fn random_bytes_returns_success_for_checked_stack_heap_and_empty_ranges() {
    for address in [0, usize::MAX, HEAP_POINTER_TAG as usize + 16] {
        let size = if address == HEAP_POINTER_TAG as usize + 16 { 32 } else { 0 };
        let p = fixture(vec![Op::Imm { dst: 0, value: address as u128 }, Op::Imm { dst: 1, value: size },
            Op::RandomBytes { dst: 0, address: 0, size: 1 }, Op::Local { dst: 2, offset: 0 },
            Op::Store { address: 2, src: 0, size: 16 }, Op::Return]);
        for engine in engines() { assert_eq!(execute_with_engine(&p, &[], Limits::default(), engine).unwrap().value, 0); }
    }
    let p = fixture(vec![Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 16 },
        Op::RandomBytes { dst: 0, address: 0, size: 1 }, Op::Local { dst: 2, offset: 0 },
        Op::Store { address: 2, src: 0, size: 16 }, Op::Return]);
    for engine in engines() { assert_eq!(execute_with_engine(&p, &[], Limits::default(), engine).unwrap().value, 0); }
}
