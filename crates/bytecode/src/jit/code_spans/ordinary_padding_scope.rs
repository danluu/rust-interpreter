//! Bind ordinary clearing spans to validated caller/callee layouts; no guest.
use super::*;
use serde_json::{Value, json};

#[test]
#[ignore = "Requires a closed exact protocol capture and its typed artifact"]
fn observe_saved_ordinary_call_layouts() {
    let bytes = std::fs::read(std::env::var("PADDING_ARTIFACT").unwrap()).unwrap();
    assert!(bytes.len() <= 128 * 1024 * 1024);
    let program: Program = bincode::deserialize(&bytes).unwrap();
    crate::validate(&program).unwrap();
    let input = std::fs::read(std::env::var("PADDING_PROTOCOL").unwrap()).unwrap();
    assert!(input.len() <= MAX_OUTPUT_BYTES);
    let protocol: Value = serde_json::from_slice(&input).unwrap();
    assert_eq!(protocol["schema_version"], 2);
    assert_eq!(protocol["status"], "passed");
    for key in ["complete_partition", "exact_full_function_reconstruction", "exact_transition_reconstruction"] {
        assert_eq!(protocol[key], true);
    }
    assert_eq!(protocol["guest_commands"], 0);
    assert_eq!(protocol["executable_code_publications"], 0);
    let mut seen = BTreeSet::new();
    let mut rows = Vec::new();
    for span in protocol["spans"].as_array().unwrap() {
        if span["kind"] != "call_frame_clear" {
            continue;
        }
        assert_eq!(span["operation"], "Call");
        assert!(span["argument"].is_null());
        let caller_id = usize::try_from(span["function"].as_u64().unwrap()).unwrap();
        let pc = usize::try_from(span["pc"].as_u64().unwrap()).unwrap();
        assert!(seen.insert((caller_id, pc)));
        let caller = &program.functions[caller_id];
        let Op::Call { function: callee_id, args, .. } = &caller.code[pc] else {
            panic!("protocol span is not a typed direct Call");
        };
        let callee = &program.functions[*callee_id];
        assert_eq!(args.len(), callee.args.len());
        rows.push(json!({
            "caller": caller_id, "pc": pc, "callee": callee_id,
            "caller_frame_align": caller.frame_align, "caller_frame_size": caller.frame_size,
            "callee_frame_align": callee.frame_align, "callee_frame_size": callee.frame_size,
            "offset": span["offset"], "end": span["end"],
        }));
        assert!(rows.len() <= 131_072);
    }
    assert!(!rows.is_empty());
    let file = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("PADDING_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file, &json!({
        "status": "passed", "artifact_sha256": format!("{:x}", Sha256::digest(&bytes)),
        "protocol_sha256": format!("{:x}", Sha256::digest(&input)),
        "code_sha256": protocol["code_sha256"], "sites": rows,
        "guest_commands": 0, "executable_code_publications": 0,
    })).unwrap();
}
