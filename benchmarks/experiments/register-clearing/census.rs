//! Typed call-site metadata for exact-code sample attribution; no guest execution.
use bincode::Options;
pub use rust_interp_bytecode::*;

// Compile the retained runtime proof itself, rather than a diagnostic facsimile.
#[allow(dead_code)]
#[path = "../../../crates/bytecode/src/registers.rs"]
mod registers;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 1 { return Err("usage: register-clearing-census PROGRAM".into()); }
    let bytes = std::fs::read(&args[0])?;
    if bytes.len() > 64 * 1024 * 1024 { return Err("artifact exceeds limit".into()); }
    let program: Program = bincode::DefaultOptions::new().with_fixint_encoding()
        .with_limit(64 * 1024 * 1024).reject_trailing_bytes().deserialize(&bytes)?;
    validate(&program)?;
    let functions: Vec<_> = program.functions.iter().enumerate().map(|(id, f)| {
        let calls: Vec<_> = f.code.iter().enumerate().filter_map(|(pc, op)| {
            if let Op::Call { function, .. } = op {
                Some(serde_json::json!({"pc": pc, "callee": function}))
            } else { None }
        }).collect();
        serde_json::json!({"id": id, "name": f.name, "code_len": f.code.len(),
            "frame_size": f.frame_size, "registers": f.registers,
            "needs_initial_zeroes": registers::needs_initial_zeroes(f), "calls": calls})
    }).collect();
    serde_json::to_writer(std::io::stdout().lock(), &functions)?;
    Ok(())
}
