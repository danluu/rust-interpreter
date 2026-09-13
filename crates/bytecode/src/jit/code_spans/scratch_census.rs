//! Reconstruct the adopted bytes with observation on/off; never publish code.
use super::*;
use serde_json::{Value, json};

fn number(value: &Value, key: &str) -> usize {
    usize::try_from(value[key].as_u64().unwrap()).unwrap()
}

#[test]
#[ignore = "Requires the bound saved unprofiled artifact, operation map and native code"]
fn observe_saved_scratch_values() {
    let artifact = std::fs::read(std::env::var("SCRATCH_ARTIFACT").unwrap()).unwrap();
    assert!(artifact.len() <= 128 * 1024 * 1024);
    let program: Program = bincode::deserialize(&artifact).unwrap();
    crate::validate(&program).unwrap();
    let mapping = std::fs::read(std::env::var("SCRATCH_MAP").unwrap()).unwrap();
    assert!(mapping.len() <= MAX_OUTPUT_BYTES);
    let mapping: Value = serde_json::from_slice(&mapping).unwrap();
    let bytes = std::fs::read(std::env::var("SCRATCH_CODE").unwrap()).unwrap();
    assert!(bytes.len() <= MAX_CODE_BYTES);
    assert_eq!(number(&mapping, "schema_version"), 1);
    assert_eq!(mapping["profiled"], false);
    for flag in ["persistent_registers", "resumable_calls", "complete", "reconstructed_bytes_match"] {
        assert_eq!(mapping[flag], true, "{flag}");
    }
    assert_eq!(number(&mapping, "code_bytes"), bytes.len());
    assert_eq!(mapping["code_sha256"], format!("{:x}", Sha256::digest(&bytes)));
    let mut plain = Jit::new_resumable(&program, false, MAX_CODE_BYTES, true).unwrap();
    plain.use_adopted_emission();
    let mut observer = Jit::new_resumable(&program, false, MAX_CODE_BYTES, true).unwrap();
    observer.use_adopted_emission();
    observer.observe_scratch_locals = true;
    let (mut cursor, mut assertions) = (0, 0);
    let mut seen = BTreeSet::new();
    let mut output = vec![];
    for function in mapping["functions"].as_array().unwrap() {
        let id = number(function, "function"); assert!(seen.insert(id));
        let f = &program.functions[id]; assert_eq!(function["name"], f.name);
        let offset = number(function, "offset"); let end = number(function, "end");
        assert_eq!(offset, cursor); assert!(offset < end && end <= bytes.len());
        assert_eq!(number(function, "assertion_base"), assertions);
        let mut collector = Collector { rows: vec![], limit: MAX_SPANS };
        let a = plain.emit_function_inner(f, (end-offset)/4, assertions, Some(&mut collector))
            .unwrap().expect("saved adopted function must reconstruct");
        let mut observed_map = Collector { rows: vec![], limit: MAX_SPANS };
        let b = observer.emit_function_inner(f, (end-offset)/4, assertions, Some(&mut observed_map))
            .unwrap().expect("observer cannot affect admission");
        verify_words(&a.words, &bytes[offset..end]).unwrap();
        assert_eq!(a.words, b.words); assert_eq!(a.assertions, b.assertions);
        assert_eq!(a.resumes, b.resumes); assert_eq!(a.operations, b.operations);
        assert!(a.scratch_hits.is_empty());
        assert_eq!(a.local_fact_events, b.local_fact_events);
        assert_eq!(a.retained_local_writes, b.retained_local_writes);
        collector.validate(f, &a).unwrap(); observed_map.validate(f, &b).unwrap();
        assert_eq!(serde_json::to_value(&collector.rows).unwrap(), serde_json::to_value(&observed_map.rows).unwrap());
        assert_eq!(a.assertions.len(), number(function, "assertion_count"));
        for row in &mut collector.rows { row.offset += offset; row.end += offset; }
        assert_eq!(serde_json::to_value(&collector.rows).unwrap(), function["spans"]);
        let load_pcs: BTreeSet<_> = collector.rows.iter().filter_map(|s| s.pc)
            .filter(|&pc| matches!(f.code[pc], Op::Load { size:8,.. })).collect();
        let mut hit_pcs = BTreeSet::new();
        for hit in &b.scratch_hits {
            assert!(load_pcs.contains(&hit.pc) && hit_pcs.insert(hit.pc));
            assert!(!a.local_fact_events.iter().any(|&(pc, kind, _)| pc == hit.pc && kind == "Load"));
            assert!(hit.origin_pc < hit.pc && hit.offset + 8 <= f.frame_size);
            assert!(matches!(f.code[hit.origin_pc], Op::Load { size:8,.. }
                | Op::Store { size:8,.. } | Op::Copy { size:8,.. }));
        }
        output.push(json!({"function":id,"name":f.name,"loads8":load_pcs,
            "already_forwarded":a.local_fact_events,"available_scratch_values":b.scratch_hits}));
        assertions += a.assertions.len(); cursor = end;
    }
    assert_eq!(cursor, bytes.len());
    assert!(plain.code.is_none() && observer.code.is_none()); assert_eq!(plain.bytes+observer.bytes, 0);
    let file = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("SCRATCH_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file, &json!({"status":"passed","code_bytes":bytes.len(),
        "code_sha256":mapping["code_sha256"],"functions":output,
        "exact_full_function_reconstruction":true,"observer_words_unchanged":true,
        "guest_commands":0,"executable_code_publications":0})).unwrap();
}
