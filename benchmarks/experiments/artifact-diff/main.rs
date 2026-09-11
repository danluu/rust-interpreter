//! Structural diagnostics only: neither normalizes bytecode nor proves equivalence.
use bincode::Options;
use rust_interp_bytecode::{Op, Program, validate};
use serde_json::{Value, json};

fn read(path: &str) -> Result<Program, Box<dyn std::error::Error>> {
    let bytes = std::fs::read(path)?;
    let program = bincode::DefaultOptions::new()
        .with_fixint_encoding()
        .with_limit(64 * 1024 * 1024)
        .reject_trailing_bytes()
        .deserialize(&bytes)?;
    validate(&program)?;
    Ok(program)
}

fn bytes(a: &[u8], b: &[u8]) -> Value {
    let positions: Vec<_> = a.iter().zip(b).enumerate()
        .filter(|(_, (x, y))| x != y).map(|(i, _)| i).collect();
    json!({"lengths": [a.len(), b.len()], "identical": a == b,
        "changed_common_bytes": positions.len(),
        "first_changes": positions.iter().take(24).map(|&i|
            json!({"offset": i, "a": a[i], "b": b[i]})).collect::<Vec<_>>()})
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let paths: Vec<_> = std::env::args().skip(1).collect();
    if paths.len() != 2 { return Err("usage: artifact-diff A.rbc B.rbc".into()); }
    let a = read(&paths[0])?;
    let b = read(&paths[1])?;
    let mut changed = vec![];
    for (index, (x, y)) in a.functions.iter().zip(&b.functions).enumerate() {
        if bincode::serialize(x)? == bincode::serialize(y)? { continue; }
        let mut ops = vec![];
        let mut count = 0;
        let mut other_changes = 0;
        for (pc, (u, v)) in x.code.iter().zip(&y.code).enumerate() {
            if bincode::serialize(u)? == bincode::serialize(v)? { continue; }
            count += 1;
            if !matches!((u, v), (Op::Imm { dst: a, .. }, Op::Imm { dst: b, .. }) if a == b) {
                other_changes += 1;
            }
            if ops.len() < 8 { ops.push(json!({"pc": pc, "a": format!("{u:?}"), "b": format!("{v:?}")})); }
        }
        let header = |f: &rust_interp_bytecode::Function| json!({"name": f.name,
            "frame_size": f.frame_size, "frame_align": f.frame_align,
            "registers": f.registers, "args": f.args, "result": f.result,
            "ops": f.code.len()});
        changed.push(json!({"index": index, "a": header(x), "b": header(y),
            "headers_identical": header(x) == header(y),
            "changed_common_ops": count, "non_immediate_changes": other_changes,
            "first_op_changes": ops}));
    }
    println!("{}", serde_json::to_string_pretty(&json!({
        "schema_version": 1, "equivalence_proof": false,
        "function_counts": [a.functions.len(), b.functions.len()],
        "entries": [a.entry, b.entry], "versions": [a.version, b.version],
        "targets": [a.target, b.target],
        "data": bytes(&a.data, &b.data), "statics": bytes(&a.statics, &b.statics),
        "thread_locals_identical": bincode::serialize(&a.thread_locals)? == bincode::serialize(&b.thread_locals)?,
        "changed_functions": changed,
    }))?);
    Ok(())
}
