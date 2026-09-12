//! Bounded structural inspection; never executes or modifies guest bytecode.
use bincode::Options;
use rust_interp_bytecode::{Op, Program};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 2 { return Err("usage: inspect PROGRAM FUNCTION-SUBSTRING".into()); }
    let bytes = std::fs::read(&args[0])?;
    let program: Program = bincode::DefaultOptions::new().with_fixint_encoding()
        .with_limit(64 * 1024 * 1024).reject_trailing_bytes().deserialize(&bytes)?;
    rust_interp_bytecode::validate(&program)?;
    for (id, f) in program.functions.iter().enumerate().filter(|(_,f)|f.name.contains(&args[1])) {
        println!("FUNCTION {id} {} frame={} registers={} args={:?} result={:?}", f.name,f.frame_size,f.registers,f.args,f.result);
        for (pc,op) in f.code.iter().enumerate() {
            println!("{pc:4}: {op:?}");
            if let Op::Call {function,..}=op {println!("      callee {}",program.functions[*function].name);}
        }
    }
    Ok(())
}
