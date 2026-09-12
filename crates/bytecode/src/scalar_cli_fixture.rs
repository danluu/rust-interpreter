use rust_interp_bytecode::{
    Binary, Function, Op, Program, Slot, VERSION,
    scalar_abi::{Artifact, FunctionAbi},
};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let directory =
        std::path::PathBuf::from(std::env::args().nth(1).ok_or("output directory required")?);
    let scalar = Function {
        name: "wrapping_add_seven".into(),
        frame_size: 32,
        frame_align: 16,
        registers: 4,
        args: vec![Slot { offset: 0, size: 8 }],
        result: Slot {
            offset: 16,
            size: 8,
        },
        code: vec![
            Op::Imm { dst: 1, value: 7 },
            Op::Binary {
                dst: 2,
                overflow: 3,
                op: Binary::Add,
                a: 0,
                b: 1,
                bits: 64,
                signed: false,
            },
            Op::Return,
        ],
    };
    let p = Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        functions: vec![scalar],
        data: vec![],
        statics: vec![],
        thread_locals: vec![],
    };
    let a = Artifact::scalar(
        p,
        vec![FunctionAbi {
            arguments: vec![Some(0)],
            result: Some(2),
        }],
    )?;
    std::fs::write(directory.join("scalar.rbc"), a.encode()?)?;
    let mut p = a.program.clone();
    p.version = VERSION;
    p.functions[0].registers = 5;
    p.functions[0].code = vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load {
            dst: 1,
            address: 0,
            size: 8,
        },
        Op::Imm { dst: 2, value: 7 },
        Op::Binary {
            dst: 3,
            overflow: 4,
            op: Binary::Add,
            a: 1,
            b: 2,
            bits: 64,
            signed: false,
        },
        Op::Local { dst: 0, offset: 16 },
        Op::Store {
            address: 0,
            src: 3,
            size: 8,
        },
        Op::Return,
    ];
    std::fs::write(directory.join("legacy.rbc"), Artifact::legacy(p)?.encode()?)?;
    let mut wrong = a.clone();
    wrong.scalar_abi[0].result = Some(99);
    std::fs::write(
        directory.join("bad-register.rbc"),
        bincode::serialize(&wrong)?,
    )?;
    let bytes = a.encode()?;
    std::fs::write(directory.join("truncated.rbc"), &bytes[..bytes.len() - 1])?;
    Ok(())
}
