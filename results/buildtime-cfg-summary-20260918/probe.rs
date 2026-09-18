// Post-export CFG-pass diagnostic only. Never executes guest code.
use bincode::Options;
use rust_interp_bytecode::{Op, Program};
use sha2::{Digest, Sha256};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::Path;
use std::time::Instant;

const LIMIT: u64 = 64 * 1024 * 1024;
const INPUT: &str = "/Users/danluu/dev/rust-interp-perf-20260912/.work/runs/local-export-adoption-token-20260912-01/artifacts/baseline/0-0.rbc";
const INPUT_SHA: &str = "d4e1314465a7bbf8ff8b74caefb1a6dc1ea87a310e6f2c716b02e7b6e5f38096";
const PROBE: &str = "/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/cfg-pass-probe";

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let total_started = Instant::now();
    let args: Vec<_> = std::env::args().collect();
    if !(args.len() == 3 || args.len() == 4)
        || !matches!(args[1].as_str(), "detail" | "summary")
        || args[2] != INPUT
    {
        return Err("usage: cfg-pass-probe detail|summary EXACT_RETAINED_RBC [NEW_PARITY_OUTPUT]".into());
    }
    let mode = args[1].as_str();
    let input = Path::new(INPUT);
    let metadata = fs::symlink_metadata(input)?;
    if !metadata.file_type().is_file() || metadata.len() > LIMIT
        || fs::canonicalize(input)? != input
    {
        return Err("input must be the retained regular file, at most 64 MiB".into());
    }
    let started = Instant::now();
    let mut bytes = Vec::new();
    File::open(input)?.take(LIMIT + 1).read_to_end(&mut bytes)?;
    if bytes.len() != 28_810_437 || bytes.len() as u64 > LIMIT {
        return Err("retained artifact size changed".into());
    }
    let read_ns = started.elapsed().as_nanos();
    let started = Instant::now();
    let input_sha = format!("{:x}", Sha256::digest(&bytes));
    if input_sha != INPUT_SHA { return Err("retained artifact digest changed".into()); }
    let input_hash_ns = started.elapsed().as_nanos();
    let version = u32::from_le_bytes(bytes.get(..4).ok_or("truncated header")?.try_into()?);
    if version != rust_interp_bytecode::VERSION {
        return Err("artifact version mismatch or partial-validation flag".into());
    }
    let started = Instant::now();
    let mut program: Program = bincode::DefaultOptions::new()
        .with_fixint_encoding().with_limit(LIMIT).reject_trailing_bytes()
        .deserialize(&bytes)?;
    let decode_ns = started.elapsed().as_nanos();
    drop(bytes);
    let started = Instant::now();
    rust_interp_bytecode::validate(&program)?;
    let validation_ns = started.elapsed().as_nanos();
    if program.functions.len() != 5421 || program.entry != 5420
        || program.target != "aarch64-apple-darwin"
    {
        return Err("retained artifact structure changed".into());
    }
    let functions = program.functions.len();
    let old_operations: usize = program.functions.iter().map(|f| f.code.len()).sum();
    let straight_line_functions = program.functions.iter().filter(|f| {
        f.code.split_last().is_some_and(|(last, prefix)| {
            matches!(last, Op::Return | Op::Trap { .. }) && prefix.iter().all(|op| {
                !matches!(op, Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. })
            })
        })
    }).count();

    // Exactly one public pass on the freshly decoded Program. Its own two
    // validation calls are included; loading, census and serialization are not.
    let started = Instant::now();
    let report = match mode {
        "detail" => rust_interp_bytecode::optimize_control_flow(&mut program)?,
        "summary" => rust_interp_bytecode::optimize_control_flow_summary(&mut program)?,
        _ => unreachable!(),
    };
    let pass_ns = started.elapsed().as_nanos();
    let new_operations: usize = program.functions.iter().map(|f| f.code.len()).sum();
    if program.functions.len() != functions || report.old_operations != old_operations
        || report.new_operations != new_operations
        || report.functions.len() != if mode == "detail" { functions } else { 0 }
    {
        return Err("CFG report/Program count mismatch".into());
    }
    let started = Instant::now();
    let output = bincode::serialize(&program)?;
    if output.len() as u64 > LIMIT { return Err("output exceeds 64 MiB".into()); }
    let serialize_ns = started.elapsed().as_nanos();
    let started = Instant::now();
    let output_sha = format!("{:x}", Sha256::digest(&output));
    let output_hash_ns = started.elapsed().as_nanos();
    let mut output_write_ns = 0;
    if let Some(destination) = args.get(3) {
        let destination = Path::new(destination);
        let parent = destination.parent().ok_or("output has no parent")?;
        if !fs::canonicalize(parent)?.starts_with(fs::canonicalize(PROBE)?) {
            return Err("parity output must be inside the owned probe directory".into());
        }
        let started = Instant::now();
        let mut file = OpenOptions::new().write(true).create_new(true).open(destination)?;
        file.write_all(&output)?;
        file.sync_all()?;
        output_write_ns = started.elapsed().as_nanos();
    }
    println!(concat!(
        "{{\"mode\":\"{}\",\"functions\":{},\"straight_line_functions\":{},",
        "\"old_operations\":{},\"new_operations\":{},\"report_functions\":{},",
        "\"output_bytes\":{},\"input_sha256\":\"{}\",\"output_sha256\":\"{}\",",
        "\"read_ns\":{},\"input_hash_ns\":{},\"decode_ns\":{},\"validation_ns\":{},",
        "\"pass_ns\":{},\"serialize_ns\":{},\"output_hash_ns\":{},",
        "\"output_write_ns\":{},\"total_ns\":{}}}"
    ), mode, functions, straight_line_functions, old_operations, new_operations,
        report.functions.len(), output.len(), input_sha, output_sha, read_ns,
        input_hash_ns, decode_ns, validation_ns, pass_ns, serialize_ns,
        output_hash_ns, output_write_ns, total_started.elapsed().as_nanos());
    Ok(())
}
