use rust_interp_bytecode::{
    Binary, Engine, Function, HEAP_POINTER_TAG, Limits, Op, Program, Slot, VERSION,
    execute_with_engine,
};

fn program(code: Vec<Op>) -> Program {
    let mut statics = vec![0; 24];
    statics[16..24].copy_from_slice(&7u64.to_le_bytes());
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 32],
        statics,
        thread_locals: vec![],
        functions: vec![Function {
            name: "static-fixture".into(),
            registers: 8,
            frame_size: 8,
            frame_align: 16,
            args: vec![],
            result: Slot { offset: 0, size: 8 },
            code,
        }],
    }
}

fn engines() -> Vec<Engine> {
    let mut engines = vec![Engine::Interpreter];
    if cfg!(all(target_arch = "aarch64", target_os = "macos")) {
        engines.push(Engine::Jit);
    }
    engines
}

#[test]
fn statics_are_mutable_without_allocator_ops_and_reset_for_each_machine() {
    let p = program(vec![
        Op::Imm {
            dst: 0,
            value: (HEAP_POINTER_TAG + 16) as u128,
        },
        Op::Load {
            dst: 1,
            address: 0,
            size: 8,
        },
        Op::Imm { dst: 2, value: 1 },
        Op::Binary {
            dst: 1,
            overflow: 3,
            op: Binary::Add,
            a: 1,
            b: 2,
            bits: 64,
            signed: false,
        },
        Op::Store {
            address: 0,
            src: 1,
            size: 8,
        },
        Op::Local { dst: 4, offset: 0 },
        Op::Copy {
            dst: 4,
            src: 0,
            size: 8,
        },
        Op::Return,
    ]);
    for engine in engines() {
        for _ in 0..2 {
            let execution = execute_with_engine(&p, &[], Limits::default(), engine).unwrap();
            assert_eq!(execution.value, 8);
            if engine == Engine::Jit {
                assert!(execution.jit_instructions > 0);
            }
        }
        let limits = Limits {
            memory: p.data.len() + p.statics.len() - 1,
            ..Limits::default()
        };
        assert!(
            execute_with_engine(&p, &[], limits, engine)
                .unwrap_err()
                .contains("initial guest data")
        );
    }
}

#[test]
fn static_copy_and_fill_preserve_constant_protection() {
    let p = program(vec![
        Op::Imm {
            dst: 0,
            value: (HEAP_POINTER_TAG + 16) as u128,
        },
        Op::Imm { dst: 1, value: 16 },
        Op::Copy {
            dst: 0,
            src: 1,
            size: 8,
        },
        Op::Imm {
            dst: 2,
            value: 0x35,
        },
        Op::Imm { dst: 3, value: 8 },
        Op::FillBytes {
            address: 0,
            value: 2,
            size: 3,
        },
        Op::Local { dst: 4, offset: 0 },
        Op::Copy {
            dst: 4,
            src: 0,
            size: 8,
        },
        Op::Return,
    ]);
    for engine in engines() {
        assert_eq!(
            execute_with_engine(&p, &[], Limits::default(), engine)
                .unwrap()
                .value,
            0x3535353535353535
        );
        for write in [
            Op::Store {
                address: 1,
                src: 0,
                size: 8,
            },
            Op::Copy {
                dst: 1,
                src: 0,
                size: 8,
            },
            Op::FillBytes {
                address: 1,
                value: 0,
                size: 0,
            },
        ] {
            let bad = program(vec![
                Op::Imm { dst: 0, value: 8 },
                Op::Imm { dst: 1, value: 16 },
                write,
                Op::Return,
            ]);
            assert!(execute_with_engine(&bad, &[], Limits::default(), engine).is_err());
        }
    }
}

#[test]
fn allocation_api_cannot_free_static_storage() {
    for engine in engines() {
        for operation in [
            Op::Deallocate {
                pointer: 0,
                size: 1,
                align: 1,
            },
            Op::Reallocate {
                dst: 3,
                pointer: 0,
                old_size: 1,
                align: 1,
                new_size: 1,
            },
        ] {
            let p = program(vec![
                Op::Imm {
                    dst: 0,
                    value: (HEAP_POINTER_TAG + 16) as u128,
                },
                Op::Imm { dst: 1, value: 8 },
                operation,
                Op::Return,
            ]);
            assert!(
                execute_with_engine(&p, &[], Limits::default(), engine)
                    .unwrap_err()
                    .contains("allocation pointer or layout mismatch")
            );
        }
    }
}
