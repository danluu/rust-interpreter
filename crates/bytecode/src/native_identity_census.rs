//! Necessary identity conditions only: no cache, code generation or guest run.
use crate::{Function, Op, Program};
use bincode::Options;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs, io::Write, path::Path, time::Instant};
mod churn;

fn digest<T: serde::Serialize>(value: &T) -> String {
    format!("{:x}", Sha256::digest(bincode::serialize(value).unwrap()))
}

fn layout(f: &Function) -> String {
    digest(&(f.frame_size, f.frame_align, f.registers, &f.args, f.result))
}

fn describe(program: &Program) -> Value {
    // Mirror the adopted emitter's global heap-mode choice, without invoking it.
    // This is NOT a complete code-cache key or a proof of emitted-code equality.
    let uses_heap = !program.statics.is_empty() || program.functions.iter().flat_map(|f| &f.code).any(|op| {
        matches!(op, Op::Allocate { .. } | Op::Deallocate { .. } | Op::Reallocate { .. }
            | Op::CAllocate { .. } | Op::CReallocate { .. } | Op::CAlignedAllocate { .. }
            | Op::CurrentDirectory { .. })
    });
    let rows: Vec<_> = program.functions.iter().enumerate().map(|(id, f)| {
        let mut calls: Vec<_> = f.code.iter().filter_map(|op| match op {
            Op::Call { function, .. } => Some(*function), _ => None,
        }).collect();
        calls.sort_unstable(); calls.dedup();
        let bytes = bincode::serialize(f).unwrap();
        json!({"id": id, "name": f.name, "body_sha256": format!("{:x}", Sha256::digest(&bytes)),
            "layout_sha256": layout(f), "serialized_bytes": bytes.len(), "operations": f.code.len(),
            "direct_callees": calls, "indirect_calls": f.code.iter().filter(|op| matches!(op, Op::CallIndirect {..})).count(),
            "assertions": f.code.iter().filter(|op| matches!(op, Op::Assert {..})).count()})
    }).collect();
    json!({"functions": rows, "version": program.version, "target": program.target,
        "uses_heap": uses_heap, "data_bytes": program.data.len(), "static_bytes": program.statics.len(),
        "data_sha256": digest(&program.data), "statics_sha256": digest(&program.statics),
        "thread_locals_sha256": digest(&program.thread_locals), "entry": program.entry,
        "global_sha256": digest(&(program.version, &program.target, program.functions.len(), uses_heap)),
        "complete_cache_key": false, "guest_commands": 0, "code_publications": 0})
}

fn bounded(path: &Path, limit: u64) -> Vec<u8> {
    let meta = fs::symlink_metadata(path).unwrap();
    assert!(meta.is_file() && meta.len() <= limit);
    fs::read(path).unwrap()
}

#[test]
fn body_identity_includes_implementation_layout_names_and_call_targets() {
    let f = Function { name: "leaf".into(), frame_size: 8, frame_align: 8, registers: 1,
        args: vec![], result: crate::Slot { offset: 0, size: 0 },
        code: vec![Op::Imm { dst: 0, value: 7 }, Op::Return] };
    let original = digest(&f);
    let mut changed = f.clone(); changed.code[0] = Op::Imm { dst: 0, value: 8 };
    assert_ne!(digest(&changed), original); assert_eq!(layout(&changed), layout(&f));
    changed = f.clone(); changed.frame_size = 16;
    assert_ne!(digest(&changed), original); assert_ne!(layout(&changed), layout(&f));
    changed = f.clone(); changed.name.push('x'); assert_ne!(digest(&changed), original);
    changed = f.clone(); changed.code[0] = Op::Call { function: 0, args: vec![], destination: 0 };
    let a = digest(&changed); changed.code[0] = Op::Call { function: 1, args: vec![], destination: 0 };
    assert_ne!(digest(&changed), a);
}

#[test]
#[ignore = "Requires closed, hash-bound real edited artifacts and a fresh output directory"]
fn observe_saved_edit_identities() {
    let input = std::env::var("NATIVE_IDENTITY_INPUT").unwrap();
    let items: Vec<Value> = serde_json::from_slice(&bounded(Path::new(&input), 1024 * 1024)).unwrap();
    assert!(!items.is_empty() && items.len() <= 32);
    for item in items {
        let start = Instant::now();
        let bytes = bounded(Path::new(item["artifact"].as_str().unwrap()), 64 * 1024 * 1024);
        let artifact_hash = format!("{:x}", Sha256::digest(&bytes));
        assert_eq!(artifact_hash, item["sha256"].as_str().unwrap());
        let read_hash_ns = start.elapsed().as_nanos(); let start = Instant::now();
        let program: Program = bincode::DefaultOptions::new().with_fixint_encoding()
            .with_limit(64 * 1024 * 1024).reject_trailing_bytes().deserialize(&bytes).unwrap();
        let decode_ns = start.elapsed().as_nanos(); let start = Instant::now();
        crate::validate(&program).unwrap();
        let validate_ns = start.elapsed().as_nanos(); let start = Instant::now();
        let mut report = describe(&program);
        let describe_ns = start.elapsed().as_nanos();
        report["artifact_sha256"] = artifact_hash.into();
        report["diagnostic_stage_ns"] = json!({"read_and_hash": read_hash_ns, "decode": decode_ns,
            "validate": validate_ns, "describe": describe_ns});
        let output = serde_json::to_vec(&report).unwrap(); assert!(output.len() <= 32 * 1024 * 1024);
        let mut file = fs::OpenOptions::new().write(true).create_new(true)
            .open(item["output"].as_str().unwrap()).unwrap();
        file.write_all(&output).unwrap(); file.write_all(b"\n").unwrap();
    }
}
