use rust_interp_bytecode::{Binary, Function, HEAP_POINTER_TAG, Op, Program, Slot, VERSION};

pub struct Case {
    pub name: &'static str,
    pub program: Program,
    pub expected: Result<u128, &'static str>,
}

fn function(name: &str, frame: usize, args: Vec<Slot>, result: Slot, code: Vec<Op>) -> Function {
    Function {
        name: name.into(),
        frame_size: frame,
        frame_align: 16,
        registers: 4,
        args,
        result,
        code,
    }
}
fn program(caller: Vec<Op>, result: Slot, callee_args: Vec<Slot>, callee_result: Slot) -> Program {
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data: vec![0; 16],
        statics: vec![],
        thread_locals: vec![],
        functions: vec![
            function("caller", 32, vec![], result, caller),
            function("callee", 32, callee_args, callee_result, vec![Op::Return]),
        ],
    }
}
fn slot(offset: usize, size: usize) -> Slot {
    Slot { offset, size }
}
fn call(args: Vec<u32>, destination: u32) -> Op {
    Op::Call {
        function: 1,
        args,
        destination,
    }
}

pub fn cases() -> Vec<Case> {
    let a = 0x0807_0605_0403_0201u128;
    let b = 0x1817_1615_1413_1211u128;
    let prefix = vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Local { dst: 1, offset: 8 },
        Op::Imm { dst: 2, value: a },
        Op::Store {
            address: 0,
            src: 2,
            size: 8,
        },
        Op::Imm { dst: 2, value: b },
        Op::Store {
            address: 1,
            src: 2,
            size: 8,
        },
        Op::Local { dst: 3, offset: 16 },
    ];
    let mut out = vec![];
    for (name, second_offset, expected) in [
        ("ordered-arguments", 8, a | b << 64),
        ("overlapping-callee-slots", 4, (a & 0xffff_ffff) | b << 32),
    ] {
        let mut code = prefix.clone();
        code.extend([call(vec![0, 1], 3), Op::Return]);
        let mut p = program(
            code,
            slot(16, 16),
            vec![slot(0, 8), slot(second_offset, 8)],
            slot(0, 16),
        );
        p.functions[1].frame_align = 4096;
        out.push(Case {
            name,
            program: p,
            expected: Ok(expected),
        });
    }
    let p = program(
        vec![
            Op::Local { dst: 0, offset: 32 },
            Op::Local { dst: 3, offset: 16 },
            call(vec![0], 3),
            Op::Return,
        ],
        slot(16, 8),
        vec![slot(0, 8)],
        slot(0, 8),
    );
    out.push(Case {
        name: "one-past-local-reads-new-callee-storage",
        program: p,
        expected: Ok(0),
    });
    let mut code = prefix.clone();
    code.extend([
        Op::Local { dst: 1, offset: 32 },
        call(vec![0, 1], 3),
        Op::Return,
    ]);
    out.push(Case {
        name: "unproven-copy-order",
        program: program(
            code,
            slot(16, 16),
            vec![slot(0, 8), slot(8, 8)],
            slot(0, 16),
        ),
        expected: Ok(a | a << 64),
    });

    let mut p = program(
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Local { dst: 1, offset: 0 },
            Op::Imm { dst: 0, value: 16 },
            Op::Imm {
                dst: 1,
                value: u128::from(HEAP_POINTER_TAG) + 16,
            },
            Op::Local { dst: 3, offset: 16 },
            call(vec![0, 1], 3),
            Op::Return,
        ],
        slot(16, 16),
        vec![slot(0, 8), slot(8, 8)],
        slot(0, 16),
    );
    p.data.extend_from_slice(&(a as u64).to_le_bytes());
    p.statics.resize(16, 0);
    p.statics.extend_from_slice(&(b as u64).to_le_bytes());
    out.push(Case {
        name: "overwritten-local-readonly-and-static-arguments",
        program: p,
        expected: Ok(a | b << 64),
    });

    let mut p = program(
        vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Local { dst: 1, offset: 16 },
            Op::Store {
                address: 0,
                src: 1,
                size: 8,
            },
            Op::Local { dst: 3, offset: 24 },
            call(vec![0], 3),
            Op::Call {
                function: 2,
                args: vec![1],
                destination: 3,
            },
            Op::Return,
        ],
        slot(24, 8),
        vec![slot(0, 8)],
        slot(0, 0),
    );
    p.functions[1].code = vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load {
            dst: 1,
            address: 0,
            size: 8,
        },
        Op::Imm { dst: 2, value: 88 },
        Op::Store {
            address: 1,
            src: 2,
            size: 8,
        },
        Op::Return,
    ];
    p.functions.push(function(
        "copy-mutated-caller",
        16,
        vec![slot(0, 8)],
        slot(0, 8),
        vec![Op::Return],
    ));
    out.push(Case {
        name: "callee-mutates-caller-through-reference",
        program: p,
        expected: Ok(88),
    });

    out.push(Case {
        name: "empty-dangling-and-frame-end-arguments",
        program: program(
            vec![
                Op::Imm {
                    dst: 0,
                    value: u128::MAX,
                },
                Op::Local { dst: 1, offset: 32 },
                Op::Local { dst: 3, offset: 16 },
                call(vec![0, 1], 0),
                Op::Imm { dst: 2, value: 42 },
                Op::Store {
                    address: 3,
                    src: 2,
                    size: 8,
                },
                Op::Return,
            ],
            slot(16, 8),
            vec![slot(0, 0), slot(32, 0)],
            slot(0, 0),
        ),
        expected: Ok(42),
    });

    for (name, code, error) in [
        (
            "invalid-argument-before-depth-error",
            vec![
                Op::Imm {
                    dst: 0,
                    value: u128::MAX,
                },
                call(vec![0], 3),
                Op::Return,
            ],
            "invalid guest memory access",
        ),
        (
            "aliased-overflow-overwrites-local",
            vec![
                Op::Local { dst: 0, offset: 0 },
                Op::Imm { dst: 2, value: 0 },
                Op::Binary {
                    dst: 1,
                    overflow: 0,
                    op: Binary::Add,
                    a: 2,
                    b: 2,
                    bits: 64,
                    signed: false,
                },
                call(vec![0], 3),
                Op::Return,
            ],
            "invalid guest memory access",
        ),
        (
            "skipped-local-is-not-a-proof",
            vec![
                Op::Jump { target: 2 },
                Op::Local { dst: 0, offset: 0 },
                call(vec![0], 3),
                Op::Return,
            ],
            "invalid guest memory access",
        ),
    ] {
        out.push(Case {
            name,
            program: program(code, slot(0, 0), vec![slot(0, 8)], slot(0, 0)),
            expected: Err(error),
        });
    }
    out
}
