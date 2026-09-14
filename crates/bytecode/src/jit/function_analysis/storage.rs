//! Offline capacity inventory; excludes BTree node storage and allocator costs.
use super::*;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::mem::size_of;

fn inventory(plan: &FunctionAnalysis) -> BTreeMap<&'static str, usize> {
    let mut fields = BTreeMap::from([
        ("inline_analysis", size_of::<FunctionAnalysis>()),
        ("register_reads", plan.reads.capacity() * size_of::<Option<(usize, usize)>>()),
        ("regions", plan.regions.capacity() * size_of::<Region>()),
        ("range_plan_boxes", plan.regions.iter().filter(|r| r.range.is_some()).count() * size_of::<range_groups::Plan>()),
        ("range_sites", plan.regions.iter().filter_map(|r| r.range.as_ref())
            .map(|p| p.sites.capacity() * size_of::<range_groups::Site>()).sum()),
        ("call_slot_buffers", plan.slots.values().map(|v| v.capacity() * size_of::<Option<usize>>()).sum()),
    ]);
    for (key, bytes) in plan.values.as_ref().map_or([
        ("liveness_bits", 0), ("successor_vector_headers", 0),
        ("successor_elements", 0), ("register_assignments", 0), ("persistent_live_masks", 0),
    ], values::Allocation::storage_capacities) { fields.insert(key, bytes); }
    fields
}

#[test]
fn inventory_includes_spare_vector_capacity_and_nested_storage() {
    let mut plan = FunctionAnalysis { reads: Vec::with_capacity(7), values: None,
        fills: BTreeMap::new(), slots: BTreeMap::new(), regions: Vec::with_capacity(3) };
    plan.slots.insert(9, Vec::with_capacity(5));
    plan.regions.push(Region { start: 0, end: 8, range: Some(Box::new(range_groups::Plan {
        root: range_groups::Root::Register(0), low: 0, high: 8, writes: false, frame_disjoint: false,
        sites: Vec::with_capacity(11),
    })) });
    let fields = inventory(&plan);
    assert_eq!(fields["register_reads"], plan.reads.capacity() * size_of::<Option<(usize, usize)>>());
    assert_eq!(fields["regions"], plan.regions.capacity() * size_of::<Region>());
    assert_eq!(fields["call_slot_buffers"], plan.slots[&9].capacity() * size_of::<Option<usize>>());
    assert_eq!(fields["range_plan_boxes"], size_of::<range_groups::Plan>());
    assert_eq!(fields["range_sites"], 11 * size_of::<range_groups::Site>());
    assert_eq!(fields["liveness_bits"], 0);
}

#[test]
#[ignore = "Requires an exact saved validated artifact and a fresh output path"]
fn observe_saved_analysis_storage() {
    let artifact = std::fs::read(std::env::var("STORAGE_ARTIFACT").unwrap()).unwrap();
    assert!(artifact.len() <= 128 * 1024 * 1024);
    let p: Program = bincode::deserialize(&artifact).unwrap(); crate::validate(&p).unwrap();
    let jit = Jit::new_resumable(&p, false, MAX_CODE_BYTES, true).unwrap();
    let mut rows = vec![];
    for (id, f) in p.functions.iter().enumerate() {
        let plan = jit.analyze_function(f);
        let fields = inventory(&plan);
        let vector_and_box_bytes: usize = fields.values().sum();
        rows.push(json!({"id":id, "name":f.name, "pcs":f.code.len(), "registers":f.registers,
            "regions":plan.regions.len(), "guarded_regions":plan.regions.iter().filter(|r|r.range.is_some()).count(),
            "liveness_admitted":plan.values.is_some(), "fields":fields,
            "vector_box_and_inline_bytes":vector_and_box_bytes,
            "excluded_test_only_liveness_buffer_bytes":plan.values.as_ref().map_or(0,values::Allocation::diagnostic_storage_bytes),
            "fill_map_entries":plan.fills.len(), "call_slot_map_entries":plan.slots.len(),
            "map_entry_tuple_bytes":plan.fills.len()*size_of::<(usize,LocalFill)>()
                + plan.slots.len()*size_of::<(usize,Vec<Option<usize>>)>()}));
        // Retain only the compact report row; do not hold every plan at once.
    }
    assert!(jit.code.is_none() && jit.assertions.is_empty() && jit.prepared.iter().all(|p| !p));
    let file = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("STORAGE_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file, &json!({"status":"passed", "artifact_sha256":format!("{:x}",Sha256::digest(&artifact)),
        "functions":rows, "guest_commands":0, "executable_code_publications":0,
        "scope":"Retained Vec capacity bytes, boxed Plan payload and inline FunctionAnalysis in this test layout. Full liveness buffers exist only under cfg(test) for diagnostic oracles and are reported separately, excluded from retained payload. Inline count includes the test-only liveness header. Map entry tuples reported separately; BTree node occupancy/links and allocator overhead excluded. Not RSS or a hard allocation bound. All validated functions, not encounter order or simultaneous runtime retention."})).unwrap();
}
