//! Offline diagnostic; no JIT allocation or guest execution.
use bincode::Options;
use sha2::{Digest, Sha256};
use std::io::Write;

fn read(path: &std::ffi::OsStr, limit: u64) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let meta = std::fs::symlink_metadata(path)?;
    if !meta.is_file() || meta.len() > limit { return Err("diagnostic input is not a bounded regular file".into()); }
    Ok(std::fs::read(path)?)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.first().is_some_and(|arg| arg == "--verify") {
        if args.len() != 4 { return Err("usage: rust-interp-lifetime-census --verify BASELINE CANDIDATE NEW_REPORT.json".into()); }
        let baseline = read(&args[1],64*1024*1024)?;
        let candidate = read(&args[2],64*1024*1024)?;
        let program: rust_interp_bytecode::Program = bincode::DefaultOptions::new()
            .with_fixint_encoding().with_limit(64*1024*1024).reject_trailing_bytes().deserialize(&baseline)?;
        let (expected,allocation) = rust_interp_bytecode::allocate_register_slots(program)?;
        let expected_bytes = bincode::serialize(&expected)?;
        let matches = expected_bytes == candidate;
        let report = serde_json::json!({"schema_version":1,"exact_allocation":matches,"allocation":allocation,
            "baseline_sha256":format!("{:x}",Sha256::digest(&baseline)),
            "candidate_sha256":format!("{:x}",Sha256::digest(&candidate)),
            "expected_sha256":format!("{:x}",Sha256::digest(&expected_bytes)),
            "scope":"Exact typed transformation, including every non-register field; no guest execution."});
        let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(&args[3])?;
        file.write_all(&serde_json::to_vec_pretty(&report)?)?;file.write_all(b"\n")?;
        if !matches { return Err("candidate differs from exact register lifetime allocation".into()); }
        return Ok(());
    }
    if !(2..=3).contains(&args.len()) {
        return Err("usage: rust-interp-lifetime-census PROGRAM NEW_REPORT.json [PROFILE.json]".into());
    }
    let bytes = read(&args[0], 64 * 1024 * 1024)?;
    let program: rust_interp_bytecode::Program = bincode::DefaultOptions::new()
        .with_fixint_encoding().with_limit(64 * 1024 * 1024).reject_trailing_bytes().deserialize(&bytes)?;
    let profile = args.get(2).map(|path| read(path, 256 * 1024 * 1024)).transpose()?;
    let mut report = rust_interp_bytecode::register_lifetime_census(&program, profile.as_deref())?;
    report["artifact_sha256"] = format!("{:x}", Sha256::digest(&bytes)).into();
    if let Some(profile) = profile { report["profile_sha256"] = format!("{:x}", Sha256::digest(&profile)).into(); }
    let output = serde_json::to_vec_pretty(&report)?;
    if output.len() > 32 * 1024 * 1024 { return Err("lifetime census exceeds 32 MiB".into()); }
    let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(&args[1])?;
    file.write_all(&output)?;file.write_all(b"\n")?;
    Ok(())
}
