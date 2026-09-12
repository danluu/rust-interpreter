//! Lowering coverage after strict analysis. No guest body is executed.
mod pack;
use crate::test_metadata as metadata;

use rustc_middle::ty::TyCtxt;
use std::path::Path;
use std::time::Instant;

pub fn read_entries(path: &Path) -> Result<Vec<String>, String> {
    let bytes = std::fs::read(path).map_err(|e| e.to_string())?;
    if bytes.len() > 8 * 1024 * 1024 { return Err("audit selection exceeds 8 MiB".into()); }
    let entries: Vec<String> = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
    let unique: std::collections::HashSet<_> = entries.iter().collect();
    if entries.is_empty() || entries.len() > 4096 || unique.len() != entries.len() ||
        entries.iter().any(|s| s.is_empty() || s.len() > 4096) {
        return Err("audit requires 1..4096 distinct, nonempty entry names of at most 4096 bytes".into());
    }
    Ok(entries)
}

pub fn report(tcx: TyCtxt<'_>, entries: &[String], retain: Option<&Path>, inline_leaves: bool, trap_unsupported_calls: bool, run_try_callbacks: bool) -> Result<serde_json::Value, String> {
    let start = Instant::now();
    let mut pack = retain.map(pack::Pack::new).transpose()?;
    let mut retention_seconds = if pack.is_some() { start.elapsed().as_secs_f64() } else { 0.0 };
    let metadata = retain.map(|_| metadata::Index::new(tcx));
    let mut records = Vec::with_capacity(entries.len());
    let mut lowered = 0;
    for (index, entry) in entries.iter().enumerate() {
        eprintln!("rust-interp-audit-entry: {}/{} {entry}", index+1, entries.len());
        let before = Instant::now();
        // A fresh export owns its allocations and indirect-call graph. Only
        // rustc's checked queries are shared between candidates. An unsupported
        // candidate cannot leave partial functions in the next one's graph.
        let result = super::lower::export(tcx, std::slice::from_ref(entry), false, true, inline_leaves, trap_unsupported_calls, run_try_callbacks, false, false)
            .and_then(|exported| {
                rust_interp_bytecode::validate(&exported.program)?;
                Ok(exported)
            });
        let mut record = match result {
            Ok(exported) => {
                let program = &exported.program;
                lowered += 1;
                let mut record = serde_json::json!({"entry":entry,"status":"lowered",
                    "functions":program.functions.len(),
                    "ops":program.functions.iter().map(|f|f.code.len()).sum::<usize>(),
                    "constant_bytes":program.data.len(),
                    "mutable_static_bytes":program.statics.len(),
                    "lowering_ms":before.elapsed().as_secs_f64()*1000.0});
                if trap_unsupported_calls {
                    record["unavailable_calls"] = serde_json::json!(exported.unavailable_calls());
                }
                if let Some(pack) = &mut pack {
                    let storing = Instant::now();
                    record["artifact"] = pack.store(index, &program)?;
                    retention_seconds += storing.elapsed().as_secs_f64();
                }
                record
            }
            Err(error) => serde_json::json!({"entry":entry,"status":"blocked",
                "error":error,"lowering_ms":before.elapsed().as_secs_f64()*1000.0}),
        };
        if let Some(metadata) = &metadata {
            record["test_metadata"] = metadata.describe(entry);
        }
        records.push(record);
        if (index+1)%25==0 || index+1==entries.len() {
            eprintln!("rust-interp-audit: {}/{} checked, {} lowered", index+1, entries.len(), lowered);
        }
    }
    let mut report = serde_json::json!({"kind":"lowering-audit","schema_version":1,
        "bytecode_version":rust_interp_bytecode::VERSION,
        "target":tcx.sess.opts.target_triple.to_string(),
        "strict_frontend":true,"executed":false,"requested":entries.len(),
        "lowered":lowered,"blocked":entries.len()-lowered,
        "lowering_seconds":start.elapsed().as_secs_f64()-retention_seconds,"entries":records});
    if inline_leaves { report["inline_leaves"] = serde_json::json!(true); }
    if trap_unsupported_calls { report["trap_unsupported_calls"] = serde_json::json!(true); }
    if run_try_callbacks { report["run_try_callbacks"] = serde_json::json!(true); }
    if let Some(pack) = pack {
        report["artifacts"] = pack.describe();
        report["artifact_retention_seconds"] = serde_json::json!(retention_seconds);
    }
    Ok(report)
}
