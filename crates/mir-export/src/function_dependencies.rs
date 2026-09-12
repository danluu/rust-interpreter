//! Observe compiler query dependencies; always recompute and verify the output.
use rustc_middle::mono::MonoItem;
use rustc_middle::ty::{Instance, TyCtxt};
use serde_json::{Value, json};
use std::time::Instant;
use sha2::{Digest, Sha256};

fn qualified_fingerprint(original: &str, namespace: &[u8; 32]) -> rustc_data_structures::fingerprint::PackedFingerprint {
    let mut hash = Sha256::new();
    hash.update(b"rust-interp-mono-item-v1\0");
    hash.update(namespace); hash.update(original.as_bytes());
    let bytes = hash.finalize();
    rustc_data_structures::fingerprint::Fingerprint::new(
        u64::from_le_bytes(bytes[..8].try_into().unwrap()),
        u64::from_le_bytes(bytes[8..16].try_into().unwrap())).into()
}

pub(crate) fn enabled() -> Result<bool, String> {
    match std::env::var_os("RUST_INTERP_FUNCTION_DEPENDENCIES") {
        None => Ok(false),
        Some(value) if value == "0" => Ok(false),
        Some(value) if value == "1" => Ok(true),
        _ => Err("RUST_INTERP_FUNCTION_DEPENDENCIES must be 0 or 1".into()),
    }
}

pub(crate) fn observe<'tcx, R>(tcx: TyCtxt<'tcx>, instance: Instance<'tcx>,
                              enabled: bool, namespace: Option<&[u8; 32]>, operation: impl FnOnce() -> R) -> (R, Option<Value>) {
    if !enabled {
        return (operation(), None);
    }
    let mut node = MonoItem::Fn(instance).codegen_dep_node(tcx);
    if let Some(namespace) = namespace {
        // This exporter rejects native codegen. Qualify its non-query node by
        // tool/policy so another namespace cannot lend us stale query edges.
        node.key_fingerprint = qualified_fingerprint(&node.key_fingerprint.to_string(), namespace);
    }
    let started = Instant::now();
    let previous_green = tcx.dep_graph.try_mark_green(tcx, &node).is_some();
    let green_check_seconds = started.elapsed().as_secs_f64();
    let result = if previous_green {
        // Marking green has already created the current node and retained its
        // edges. Re-execution verifies the output without duplicating the node.
        tcx.dep_graph.with_ignore(operation)
    } else {
        let (result, index) = tcx.dep_graph.with_task(node, tcx, operation, None);
        tcx.dep_graph.read_index(index);
        result
    };
    (result, Some(json!({"node": format!("{}", node.key_fingerprint),
        "kind": format!("{:?}", node.kind), "previous_green": previous_green,
        "namespace_qualified": namespace.is_some(),
        "green_check_seconds": green_check_seconds, "lowering_executed": true})))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn tool_policy_namespace_and_unambiguous_instance_key_both_qualify_the_node() {
        assert_eq!(qualified_fingerprint("1-23", &[1; 32]), qualified_fingerprint("1-23", &[1; 32]));
        assert_ne!(qualified_fingerprint("1-23", &[1; 32]), qualified_fingerprint("1-23", &[2; 32]));
        assert_ne!(qualified_fingerprint("1-23", &[1; 32]), qualified_fingerprint("12-3", &[1; 32]));
    }
}
