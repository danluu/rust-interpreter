//! Offline diagnostic; never creates a JIT or executes a guest instruction.
use sha2::{Digest, Sha256};
use bincode::Options;
use std::{io::Write, path::PathBuf};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if !(2..=3).contains(&args.len()) {
        return Err("usage: rust-interp-register-census PROGRAM NEW_REPORT.json [PROFILE.json]".into());
    }
    let input = PathBuf::from(&args[0]);
    let metadata = std::fs::symlink_metadata(&input)?;
    if !metadata.is_file() || metadata.len() > 64 * 1024 * 1024 {
        return Err("census requires a regular bytecode file of at most 64 MiB".into());
    }
    let bytes = std::fs::read(&input)?;
    let program: rust_interp_bytecode::Program = bincode::DefaultOptions::new()
        .with_fixint_encoding().with_limit(64 * 1024 * 1024).reject_trailing_bytes().deserialize(&bytes)?;
    let mut report = if let Some(path) = args.get(2) {
        let meta = std::fs::symlink_metadata(path)?;
        if !meta.is_file() || meta.len() > 256 * 1024 * 1024 {
            return Err("profile requires a regular file of at most 256 MiB".into());
        }
        let profile = std::fs::read(path)?;
        let mut report = rust_interp_bytecode::register_width_profile_census(&program, &profile)?;
        report["profile_sha256"] = format!("{:x}", Sha256::digest(&profile)).into();
        report
    } else { rust_interp_bytecode::register_width_census(&program)? };
    report["artifact_sha256"] = format!("{:x}", Sha256::digest(&bytes)).into();
    let output = serde_json::to_vec_pretty(&report)?;
    if output.len() > 32 * 1024 * 1024 { return Err("census report exceeds 32 MiB".into()); }
    let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(&args[1])?;
    file.write_all(&output)?; file.write_all(b"\n")?;
    Ok(())
}
