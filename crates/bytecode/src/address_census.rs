//! Offline diagnostic: no JIT construction or guest execution.
use bincode::Options;
use sha2::{Digest, Sha256};
use std::{io::Write, path::Path};

fn read_bounded(path: &Path, limit: u64) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let meta = std::fs::symlink_metadata(path)?;
    if !meta.is_file() || meta.len() > limit {
        return Err("census input must be a bounded regular file".into());
    }
    let data = std::fs::read(path)?;
    if data.len() as u64 > limit { return Err("census input grew beyond its bound".into()); }
    Ok(data)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args: Vec<_> = std::env::args_os().skip(1).collect();
    let region_facts = args.first().is_some_and(|a| a == "--region-facts");
    let range_groups = args.first().is_some_and(|a| a == "--range-groups");
    let disjoint = args.first().is_some_and(|a| a == "--disjoint-frame");
    if region_facts || range_groups || disjoint { args.remove(0); }
    if args.len() != 3 {
        return Err("usage: rust-interp-address-census [--region-facts|--range-groups|--disjoint-frame] PROGRAM NEW_REPORT.json PROFILE.json".into());
    }
    let bytes = read_bounded(Path::new(&args[0]), 64 * 1024 * 1024)?;
    let program: rust_interp_bytecode::Program = bincode::DefaultOptions::new()
        .with_fixint_encoding().with_limit(64 * 1024 * 1024).reject_trailing_bytes().deserialize(&bytes)?;
    let profile = read_bounded(Path::new(&args[2]), 256 * 1024 * 1024)?;
    let mut report = if disjoint {
        rust_interp_bytecode::disjoint_frame_census(&program, &profile)?
    } else if range_groups {
        rust_interp_bytecode::range_group_census(&program, &profile)?
    } else if region_facts {
        rust_interp_bytecode::region_fact_census(&program, &profile)?
    } else {
        rust_interp_bytecode::address_reuse_census(&program, &profile)?
    };
    report["artifact_sha256"] = format!("{:x}", Sha256::digest(&bytes)).into();
    report["profile_sha256"] = format!("{:x}", Sha256::digest(&profile)).into();
    let output = serde_json::to_vec_pretty(&report)?;
    if output.len() > 32 * 1024 * 1024 { return Err("census report exceeds 32 MiB".into()); }
    let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(&args[1])?;
    file.write_all(&output)?;
    file.write_all(b"\n")?;
    Ok(())
}
