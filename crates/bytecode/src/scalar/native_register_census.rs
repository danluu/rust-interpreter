//! Explicit saved-artifact emission diagnostic; never publishes executable code.
use super::*;
use serde_json::{Value as Json, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

fn storage(emitted: &Emitted) -> Json {
    let count = |opcode| emitted.words.iter().filter(|&&word|
        word & 0xffc00000 == opcode && (word >> 5) & 31 == 31).count();
    json!({"bytes": emitted.words.len()*4, "stack_bytes": emitted.stack_bytes,
        "register_values": emitted.register_values,
        "static_stack_loads": count(0xf9400000), "static_stack_stores": count(0xf9000000)})
}

#[test]
#[ignore = "Requires a pinned original artifact and closed scalar code-map references"]
fn observe_original_scalar_register_storage() {
    let artifact = std::fs::read(std::env::var("SCALAR_REGISTER_ARTIFACT").unwrap()).unwrap();
    assert!(artifact.len() <= 128*1024*1024);
    let p: crate::Program = bincode::deserialize(&artifact).unwrap();
    crate::validate(&p).unwrap();
    let references: Json = serde_json::from_slice(&std::fs::read(
        std::env::var("SCALAR_REGISTER_REFERENCES").unwrap()).unwrap()).unwrap();
    let mut old_bodies = BTreeMap::new();
    for reference in references.as_array().unwrap() {
        let map: Json = serde_json::from_slice(&std::fs::read(reference["map"].as_str().unwrap()).unwrap()).unwrap();
        let code = std::fs::read(reference["code"].as_str().unwrap()).unwrap();
        assert!(code.len() <= 16*1024*1024);
        assert_eq!(map["architecture"], "aarch64");
        assert_eq!(map["profiled"], true);
        assert_eq!(format!("{:x}", Sha256::digest(&code)), reference["code_sha256"]);
        for range in map["ranges"].as_array().unwrap() {
            if range["kind"] != "scalar_leaf" { continue; }
            let id = range["function"].as_u64().unwrap() as usize;
            assert_eq!(range["name"], p.functions[id].name);
            let start = range["offset"].as_u64().unwrap() as usize;
            let end = range["end"].as_u64().unwrap() as usize;
            assert!(start < end && end <= code.len() && (end-start)%4 == 0);
            let words = code[start..end].chunks_exact(4)
                .map(|b|u32::from_le_bytes(b.try_into().unwrap())).collect::<Vec<_>>();
            if let Some(previous) = old_bodies.insert(id, words.clone()) { assert_eq!(previous, words); }
        }
    }
    assert!(!old_bodies.is_empty());
    let mut work = crate::proof::MAX_GLOBAL_WORK;
    let mut rows = vec![];
    let mut reconstructed = 0;
    for (id, f) in p.functions.iter().enumerate() {
        let memory = crate::proof::memory_plan(&p, id, &mut work);
        let Ok(plan) = lower(f, &memory, 250_000) else { continue; };
        let Ok(old) = emit_with_registers(&plan, false, false) else { continue; };
        let new = emit(&plan, false).unwrap();
        if let Some(words) = old_bodies.get(&id) {
            assert_eq!(&emit_with_registers(&plan, true, false).unwrap().words, words,
                "spilled reference differs from qualified native body {id}");
            reconstructed += 1;
        }
        assert!(new.stack_bytes <= old.stack_bytes);
        rows.push(json!({"function":id,"name":f.name,"before":storage(&old),"after":storage(&new)}));
    }
    assert_eq!(reconstructed, old_bodies.len());
    assert_eq!(rows.len(), 478);
    let output = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("SCALAR_REGISTER_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(output, &json!({"status":"passed","functions":rows,
        "old_bodies_reconstructed":reconstructed,"guest_commands":0,"executable_code_publications":0,
        "performance_measurement":false,"limitation":"Static storage and word counts are not dynamic hardware instruction counts or speedups."})).unwrap();
}
