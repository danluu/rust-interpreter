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
    if args.first().is_some_and(|v|v == "--fold" || v == "--verify-fold" || v == "--specialize" || v == "--verify-specialize") {
        if args.len()!=4 {return Err("usage: rust-interp-call-census --fold|--verify-fold|--specialize|--verify-specialize BASELINE OUTPUT_OR_CANDIDATE NEW_REPORT.json".into());}
        let bytes=read(&args[1],64*1024*1024)?;
        let program:rust_interp_bytecode::Program=bincode::DefaultOptions::new().with_fixint_encoding()
            .with_limit(64*1024*1024).reject_trailing_bytes().deserialize(&bytes)?;
        let started=std::time::Instant::now();
        let specializing=args[0]=="--specialize" || args[0]=="--verify-specialize";
        let (mut folded,details)=if specializing {rust_interp_bytecode::specialize_constant_calls(program)?} else {rust_interp_bytecode::fold_constants(program)?};
        let cfg=if specializing {None} else {Some(rust_interp_bytecode::optimize_control_flow(&mut folded)?)};
        let seconds=started.elapsed().as_secs_f64();
        let expected=bincode::serialize(&folded)?;
        if expected.len()>64*1024*1024 {return Err("folded artifact exceeds 64 MiB".into());}
        let verify=args[0]=="--verify-fold" || args[0]=="--verify-specialize";
        let candidate=if verify {read(&args[2],64*1024*1024)?} else {expected.clone()};
        let matches=candidate==expected;
        let mut report=serde_json::json!({"schema_version":1,
            "baseline_sha256":format!("{:x}",Sha256::digest(&bytes)),"candidate_sha256":format!("{:x}",Sha256::digest(&candidate)),
            "expected_sha256":format!("{:x}",Sha256::digest(&expected)),"diagnostic_transform_seconds":seconds,
            "performance_measurement":false,"scope":"Exact whole-artifact typed folding and CFG cleanup; no guest execution or runtime speed claim."});
        if specializing {
            report["exact_constant_specialization"]=matches.into();report["specialization"]=details;
            report["scope"]="Exact whole-artifact typed direct-call specialization; no guest execution or runtime speed claim.".into();
        } else {
            report["exact_constant_fold"]=matches.into();report["fold"]=details;
            report["control_flow"]=serde_json::to_value(cfg.unwrap())?;
        }
        let output=serde_json::to_vec_pretty(&report)?;
        if output.len()>32*1024*1024 {return Err("folding report exceeds 32 MiB".into());}
        // Report publication is last. An incomplete command is never a ready
        // artifact/report pair; all output paths must be new.
        let mut report_file=std::fs::OpenOptions::new().write(true).create_new(true).open(&args[3])?;
        if !verify {std::fs::OpenOptions::new().write(true).create_new(true).open(&args[2])?.write_all(&expected)?;}
        report_file.write_all(&output)?;report_file.write_all(b"\n")?;
        if !matches {return Err("candidate differs from exact typed transformation".into());}
        return Ok(());
    }
    if !(2..=3).contains(&args.len()) {
        return Err("usage: rust-interp-call-census PROGRAM NEW_REPORT.json [PROFILE.json]".into());
    }
    let bytes = read(&args[0], 64 * 1024 * 1024)?;
    let program: rust_interp_bytecode::Program = bincode::DefaultOptions::new()
        .with_fixint_encoding().with_limit(64 * 1024 * 1024).reject_trailing_bytes().deserialize(&bytes)?;
    let profile = args.get(2).map(|path| read(path, 256 * 1024 * 1024)).transpose()?;
    let mut report = rust_interp_bytecode::constant_call_argument_census(&program, profile.as_deref())?;
    report["artifact_sha256"] = format!("{:x}", Sha256::digest(&bytes)).into();
    if let Some(profile) = profile { report["profile_sha256"] = format!("{:x}", Sha256::digest(&profile)).into(); }
    let output = serde_json::to_vec_pretty(&report)?;
    if output.len() > 32 * 1024 * 1024 { return Err("call census exceeds 32 MiB".into()); }
    let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(&args[1])?;
    file.write_all(&output)?;file.write_all(b"\n")?;
    Ok(())
}
