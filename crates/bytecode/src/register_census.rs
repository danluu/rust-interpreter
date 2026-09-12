//! Offline diagnostic; never creates a JIT or executes a guest instruction.
use sha2::{Digest, Sha256};
use std::{io::Write, path::PathBuf};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.len() != 2 { return Err("usage: rust-interp-register-census PROGRAM NEW_REPORT.json".into()); }
    let input = PathBuf::from(&args[0]);
    let metadata = std::fs::symlink_metadata(&input)?;
    if !metadata.is_file() || metadata.len() > 64 * 1024 * 1024 {
        return Err("census requires a regular bytecode file of at most 64 MiB".into());
    }
    let bytes = std::fs::read(&input)?;
    let program: rust_interp_bytecode::Program = bincode::deserialize(&bytes)?;
    let mut report = rust_interp_bytecode::register_width_census(&program)?;
    report["artifact_sha256"] = format!("{:x}", Sha256::digest(&bytes)).into();
    let output = serde_json::to_vec_pretty(&report)?;
    if output.len() > 32 * 1024 * 1024 { return Err("census report exceeds 32 MiB".into()); }
    let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(&args[1])?;
    file.write_all(&output)?; file.write_all(b"\n")?;
    Ok(())
}
