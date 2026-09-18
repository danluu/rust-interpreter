// Actual public leaf-inlining API; no guest execution or private-pass copy.
use bincode::Options;
use rust_interp_bytecode::{LeafInlineOptions, Op, Program};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::Path;
use std::time::Instant;

const LIMIT: u64 = 64 * 1024 * 1024;
const REPORT_LIMIT: usize = 8 * 1024 * 1024;
const INPUT: &str = "/Users/danluu/dev/rust-interp-perf-20260912/.work/runs/local-export-adoption-token-20260912-01/artifacts/baseline/0-0.rbc";
const INPUT_SHA: &str = "d4e1314465a7bbf8ff8b74caefb1a6dc1ea87a310e6f2c716b02e7b6e5f38096";
const PROBE: &str = "/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/inline-pass-probe";

// Shape counts only: no scalar whitelist, local-site proof, register proof,
// recursion analysis, or selection algorithm is copied into the probe.
fn census(program: &Program, options: LeafInlineOptions) -> Value {
    let size_bounded: Vec<_> = program.functions.iter().map(|f| {
        f.code.len() > 1 && f.code.len() <= options.leaf_operations
            && f.frame_size <= 512 && f.registers <= 256 && f.result.size <= 128
            && f.args.iter().all(|arg| arg.size <= 128)
    }).collect();
    let mut operations = 0;
    let mut direct_calls = 0;
    let mut indirect_calls = 0;
    let mut direct_callers = 0;
    let mut indirect_only_callers = 0;
    let mut calls_to_size_bounded_functions = 0;
    for f in &program.functions {
        operations += f.code.len();
        let (mut direct, mut indirect) = (0, 0);
        for op in &f.code {
            match op {
                Op::Call { function, .. } => {
                    direct += 1;
                    calls_to_size_bounded_functions += usize::from(size_bounded[*function]);
                }
                Op::CallIndirect { .. } => indirect += 1,
                _ => {}
            }
        }
        direct_calls += direct;
        indirect_calls += indirect;
        direct_callers += usize::from(direct != 0);
        indirect_only_callers += usize::from(direct == 0 && indirect != 0);
    }
    json!({"functions":program.functions.len(), "operations":operations,
        "direct_calls":direct_calls, "indirect_calls":indirect_calls,
        "direct_callers":direct_callers,
        "no_direct_call_functions":program.functions.len()-direct_callers,
        "indirect_only_callers":indirect_only_callers,
        "size_bounded_functions_not_eligibility":size_bounded.iter().filter(|x| **x).count(),
        "calls_to_size_bounded_functions_not_eligibility":calls_to_size_bounded_functions,
        "functions_above_leaf_operation_limit":program.functions.iter()
            .filter(|f| f.code.len()>options.leaf_operations).count(),
        "graph_scan_within_current_limits":program.functions.len()<=65_536
            && direct_calls<=500_000 && operations<=2_000_000})
}

fn write_new(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(bytes)?;
    file.sync_all()
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let total_started = Instant::now();
    let args: Vec<_> = std::env::args().collect();
    if !(args.len()==3 || args.len()==4)
        || !matches!(args[1].as_str(), "census" | "pass") || args[2]!=INPUT
        || (args[1]=="census" && args.len()!=3)
    {
        return Err("usage: inline-pass-probe census|pass EXACT_RETAINED_RBC [NEW_PARITY_DIRECTORY]".into());
    }
    let input = Path::new(INPUT);
    let metadata = fs::symlink_metadata(input)?;
    if !metadata.file_type().is_file() || metadata.len()>LIMIT || fs::canonicalize(input)?!=input {
        return Err("retained input must be regular, canonical and at most 64 MiB".into());
    }
    let started = Instant::now();
    let mut bytes = Vec::new();
    File::open(input)?.take(LIMIT+1).read_to_end(&mut bytes)?;
    if bytes.len()!=28_810_437 { return Err("retained input size changed".into()); }
    let read_ns = started.elapsed().as_nanos();
    let started = Instant::now();
    if format!("{:x}",Sha256::digest(&bytes))!=INPUT_SHA { return Err("retained input digest changed".into()); }
    let input_hash_ns = started.elapsed().as_nanos();
    let version = u32::from_le_bytes(bytes.get(..4).ok_or("truncated header")?.try_into()?);
    if version!=rust_interp_bytecode::VERSION { return Err("version mismatch or partial validation".into()); }
    let started = Instant::now();
    let original: Program = bincode::DefaultOptions::new().with_fixint_encoding()
        .with_limit(LIMIT).reject_trailing_bytes().deserialize(&bytes)?;
    let decode_ns = started.elapsed().as_nanos();
    drop(bytes);
    let started = Instant::now();
    rust_interp_bytecode::validate(&original)?;
    let validation_ns = started.elapsed().as_nanos();
    if original.functions.len()!=5421 || original.entry!=5420 || original.target!="aarch64-apple-darwin" {
        return Err("retained structure changed".into());
    }
    let options = LeafInlineOptions::default();
    if (options.leaf_operations,options.caller_growth,options.program_growth_percent)!=(192,4096,50) {
        return Err("public default options changed".into());
    }
    let started = Instant::now();
    let shape = census(&original,options);
    let census_ns = started.elapsed().as_nanos();
    let mut metrics = json!({"mode":args[1],"input_sha256":INPUT_SHA,"census":shape,
        "options":{"leaf_operations":192,"caller_growth":4096,"program_growth_percent":50},
        "read_ns":read_ns,"input_hash_ns":input_hash_ns,"decode_ns":decode_ns,
        "validation_ns":validation_ns,"census_ns":census_ns});
    if args[1]=="census" {
        metrics["total_ns"]=json!(total_started.elapsed().as_nanos());
        println!("{metrics}");
        return Ok(());
    }

    // Exactly one actual public API call. Includes its original Program clone,
    // complete report creation, initial validation and output validation.
    let started = Instant::now();
    let (program, report) = rust_interp_bytecode::inline_leaves(&original,options)?;
    metrics["pass_ns"]=json!(started.elapsed().as_nanos());
    let new_operations: usize = program.functions.iter().map(|f| f.code.len()).sum();
    if program.functions.len()!=original.functions.len()
        || report["original_operations"]!=metrics["census"]["operations"]
        || report["new_operations"]!=json!(new_operations)
    {
        return Err("public report/Program count mismatch".into());
    }
    let selected_sites = report["selected_sites"].as_u64().ok_or("missing selected_sites")?;
    let changed_callers = report["changed_callers"].as_array().ok_or("missing changed_callers")?.len();
    let started = Instant::now();
    let output = bincode::serialize(&program)?;
    if output.len() as u64>LIMIT { return Err("output exceeds 64 MiB".into()); }
    metrics["serialize_ns"]=json!(started.elapsed().as_nanos());
    let started = Instant::now();
    let output_sha = format!("{:x}",Sha256::digest(&output));
    metrics["output_hash_ns"]=json!(started.elapsed().as_nanos());
    let started = Instant::now();
    let report_bytes = serde_json::to_vec(&report)?;
    if report_bytes.len()>REPORT_LIMIT { return Err("report exceeds 8 MiB".into()); }
    let report_sha = format!("{:x}",Sha256::digest(&report_bytes));
    metrics["report_serialize_hash_ns"]=json!(started.elapsed().as_nanos());
    metrics["selected_sites"]=json!(selected_sites);
    metrics["changed_callers"]=json!(changed_callers);
    metrics["new_operations"]=json!(new_operations);
    metrics["output_bytes"]=json!(output.len());
    metrics["output_sha256"]=json!(output_sha);
    metrics["report_bytes"]=json!(report_bytes.len());
    metrics["report_sha256"]=json!(report_sha);
    metrics["output_write_ns"]=json!(0);
    if let Some(destination) = args.get(3) {
        let destination = Path::new(destination);
        let parent = destination.parent().ok_or("parity directory has no parent")?;
        if !fs::canonicalize(parent)?.starts_with(fs::canonicalize(PROBE)?) {
            return Err("parity directory must be inside the owned probe directory".into());
        }
        let started = Instant::now();
        fs::create_dir(destination)?;
        write_new(&destination.join("program.rbc"),&output)?;
        write_new(&destination.join("report.json"),&report_bytes)?;
        metrics["output_write_ns"]=json!(started.elapsed().as_nanos());
    }
    metrics["total_ns"]=json!(total_started.elapsed().as_nanos());
    println!("{metrics}");
    Ok(())
}
