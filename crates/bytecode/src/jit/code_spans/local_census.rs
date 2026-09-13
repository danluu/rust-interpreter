//! Offline comparison only: no executable memory is allocated or published.
use super::*;
use serde_json::{Value, json};

fn number(value: &Value, key: &str) -> usize {
    usize::try_from(value[key].as_u64().unwrap()).unwrap()
}

#[test]
#[ignore = "Requires a bound artifact, saved operation map and exact native code"]
fn observe_saved_local_facts() {
    let artifact = std::fs::read(std::env::var("LOCAL_CENSUS_ARTIFACT").unwrap()).unwrap();
    assert!(artifact.len() <= 128 * 1024 * 1024);
    let program: Program = bincode::deserialize(&artifact).unwrap();
    crate::validate(&program).unwrap();
    let mapping = std::fs::read(std::env::var("LOCAL_CENSUS_MAP").unwrap()).unwrap();
    assert!(mapping.len() <= MAX_OUTPUT_BYTES);
    let mapping: Value = serde_json::from_slice(&mapping).unwrap();
    let bytes = std::fs::read(std::env::var("LOCAL_CENSUS_CODE").unwrap()).unwrap();
    assert!(bytes.len() <= MAX_CODE_BYTES);
    assert_eq!(number(&mapping, "schema_version"), 1);
    for flag in ["profiled", "persistent_registers", "resumable_calls", "complete", "reconstructed_bytes_match"] {
        assert_eq!(mapping[flag], true, "{flag}");
    }
    assert_eq!(number(&mapping, "code_bytes"), bytes.len());
    assert_eq!(mapping["code_sha256"], format!("{:x}", Sha256::digest(&bytes)));
    let mut baseline = Jit::new_resumable(&program, true, MAX_CODE_BYTES, true).unwrap().use_adopted_emission();
    baseline.observe_guarded_local_retention = false;
    baseline.observe_static_local_facts = false;
    baseline.observe_scalar_copy = false;
    let mut alternative = Jit::new_resumable(&program, true, MAX_CODE_BYTES, true).unwrap().use_adopted_emission();
    alternative.observe_guarded_local_retention = true;
    let static_facts = match std::env::var("LOCAL_CENSUS_STATIC_FACTS").ok().as_deref() {
        None | Some("0") => false, Some("1") => true, _ => panic!("invalid static-fact census option"),
    };
    alternative.observe_static_local_facts = static_facts;
    let scalar_copy = match std::env::var("LOCAL_CENSUS_SCALAR_COPY").ok().as_deref() {
        None | Some("0") => false, Some("1") => true, _ => panic!("invalid scalar-copy census option"),
    };
    alternative.observe_scalar_copy = scalar_copy;
    let mut output = vec![];
    let (mut cursor, mut assertions, mut candidate_bytes) = (0, 0, 0);
    let mut seen = BTreeSet::new();
    for function in mapping["functions"].as_array().unwrap() {
        let id = number(function, "function");
        assert!(seen.insert(id));
        let f = &program.functions[id];
        assert_eq!(function["name"], f.name);
        let offset = number(function, "offset");
        let end = number(function, "end");
        assert_eq!(offset, cursor);
        assert!(offset < end && end <= bytes.len());
        assert_eq!(number(function, "assertion_base"), assertions);
        let mut control_map = Collector { rows: vec![], limit: MAX_SPANS };
        let control = baseline.emit_function_inner(f, (end-offset)/4, assertions, Some(&mut control_map))
            .unwrap().expect("saved baseline must reconstruct");
        verify_words(&control.words, &bytes[offset..end]).unwrap();
        control_map.validate(f, &control).unwrap();
        assert_eq!(control.assertions.len(), number(function, "assertion_count"));
        for row in &mut control_map.rows { row.offset += offset; row.end += offset; }
        assert_eq!(serde_json::to_value(&control_map.rows).unwrap(), function["spans"]);
        let mut candidate_map = Collector { rows: vec![], limit: MAX_SPANS };
        // Candidate admission uses its own cumulative staging consumption.
        let candidate = alternative.emit_function_inner(f, (MAX_CODE_BYTES-candidate_bytes)/4,
            assertions, Some(&mut candidate_map)).unwrap();
        let candidate = if let Some(candidate) = candidate {
            candidate_map.validate(f, &candidate).unwrap();
            assert_eq!(control.assertions, candidate.assertions);
            assert_eq!(control.operations, candidate.operations);
            assert_eq!(control.entries.iter().map(|r|r.map(|r|r.end)).collect::<Vec<_>>(),
                       candidate.entries.iter().map(|r|r.map(|r|r.end)).collect::<Vec<_>>());
            candidate_bytes += candidate.words.len()*4;
            json!({"status":"emitted","bytes":candidate.words.len()*4,
                "forwarding":candidate.local_fact_events,"retained_writes":candidate.retained_local_writes,
                "spans":candidate_map.rows,"words_equal":control.words==candidate.words})
        } else { json!({"status":"declined"}) };
        assert!(control.retained_local_writes.is_empty());
        // Control spans are global offsets; candidate spans are function-relative.
        output.push(json!({"function":id,"name":f.name,"baseline_offset":offset,"baseline_end":end,
            "assertion_base":assertions,"baseline_forwarding":control.local_fact_events,"candidate":candidate}));
        assertions += control.assertions.len(); cursor = end;
    }
    assert_eq!(cursor, bytes.len());
    assert!(baseline.code.is_none() && alternative.code.is_none());
    assert_eq!(baseline.bytes + alternative.bytes, 0);
    let file = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("LOCAL_CENSUS_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file, &json!({"status":"passed","baseline_bytes":bytes.len(),
        "candidate_bytes":candidate_bytes,"static_fact_preservation":static_facts,"scalar_copy":scalar_copy,"functions":output,"exact_baseline_reconstruction":true,
        "guest_commands":0,"executable_code_publications":0,"capacity":MAX_CODE_BYTES})).unwrap();
}
